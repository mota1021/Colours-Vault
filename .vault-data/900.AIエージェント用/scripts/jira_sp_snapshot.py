"""
Colours Jira チケットスナップショット生成スクリプト。

Jira (SCRUM) の現行マイルストーン配下を取得し、Jiraキーを一意識別子、
Jira summary を人間向け名称として `チケットスナップショット.md` を冪等更新する。
旧 `元ID:*`（CS-5 / EW-5 / PL-3b 等）ラベルは参照しない。

実行:
    python jira_sp_snapshot.py
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parents[2]
VAULT_ROOT = next((p for p in SCRIPT_DIR.parents if (p / ".git").exists()), SCRIPT_DIR.parents[6])
ENV_PATH = VAULT_ROOT / ".env"
OUTPUT_PATH = SHARED_ROOT / "900.AIエージェント用" / "チケットスナップショット.md"

REQUIRED_ENV_KEYS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "CURRENT_MILESTONE_EPIC")
COLUMNS = ("Jiraキー", "名称", "状態", "カテゴリ", "担当", "後続チケット", "先行チケット", "着手開始日")
ISSUE_FIELDS = "summary,status,labels,issuelinks,assignee"
CATEGORY_LABEL_RE = re.compile(r"^分類:(.+)$")
JIRA_NUMBER_RE = re.compile(r"(\d+)$")
# Jira summary に歴史的に付いている表示prefixだけ除去する。識別には使わない。
LEGACY_SP_SUMMARY_PREFIX_RE = re.compile(r"^\[SP-\d+\]\s*")
API_TOKEN_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"


def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def jira_number(key: str) -> int:
    m = JIRA_NUMBER_RE.search(key or "")
    return int(m.group(1)) if m else 0


def load_env(path: Path) -> dict:
    env = {key: os.environ.get(key, "") for key in REQUIRED_ENV_KEYS}
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key in REQUIRED_ENV_KEYS and not env.get(key):
                env[key] = value
    missing = [k for k in REQUIRED_ENV_KEYS if not env.get(k)]
    if missing:
        fail(f"必要な環境変数が不足しています: {', '.join(missing)}")
    return env


def fetch_issues(base_url: str, email: str, token: str, milestone: str) -> list:
    url = f"{base_url.rstrip('/')}/rest/api/3/search/jql"
    auth = (email, token)
    headers = {"Accept": "application/json"}
    jql = f"project = SCRUM AND parent = {milestone} ORDER BY key ASC"
    issues, next_token = [], None
    while True:
        params = {"jql": jql, "fields": ISSUE_FIELDS, "maxResults": 100}
        if next_token:
            params["nextPageToken"] = next_token
        try:
            resp = requests.get(url, params=params, auth=auth, headers=headers, timeout=30)
        except requests.exceptions.RequestException as exc:
            fail(f"Jira APIへの接続に失敗しました: {exc}")
        if resp.status_code == 401:
            fail(f"Jira認証エラー（401）。{API_TOKEN_URL} でトークンを確認してください。")
        if not resp.ok:
            fail(f"Jira APIエラー HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
        except ValueError:
            fail("Jira APIレスポンスをJSONとして解析できませんでした。")
        issues.extend(data.get("issues", []))
        if data.get("isLast", True):
            break
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    return issues


def category_from(labels: list) -> str:
    for label in labels or []:
        m = CATEGORY_LABEL_RE.match(label)
        if m:
            return m.group(1)
    return "-"


def display_name(summary: str) -> str:
    """Jira summary を表示名へ整形する。旧SP prefixは表示上だけ除去する。"""
    return LEGACY_SP_SUMMARY_PREFIX_RE.sub("", summary or "").strip()


def extract_record(issue: dict) -> dict:
    key = issue.get("key", "?")
    fields = issue.get("fields") or {}
    outward, inward = [], []
    for link in fields.get("issuelinks") or []:
        if (link.get("type") or {}).get("name") != "Blocks":
            continue
        if "outwardIssue" in link:
            outward.append(link["outwardIssue"]["key"])
        if "inwardIssue" in link:
            inward.append(link["inwardIssue"]["key"])
    outward.sort(key=jira_number)
    inward.sort(key=jira_number)
    return {
        "Jiraキー": key,
        "名称": display_name(fields.get("summary") or ""),
        "状態": (fields.get("status") or {}).get("name", ""),
        "カテゴリ": category_from(fields.get("labels") or []),
        "担当": (fields.get("assignee") or {}).get("displayName") or "-",
        "後続チケット": ", ".join(outward) if outward else "-",
        "先行チケット": ", ".join(inward) if inward else "-",
    }


def parse_existing_start_dates(path: Path) -> dict:
    """既存スナップショットから Jiraキー→着手開始日 を引き継ぐ。

    旧形式にも Jiraキー列が存在するため、旧独自IDへ依存せずそのまま移行できる。
    """
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("|") or "Jiraキー" not in line or "着手開始日" not in line:
            continue
        headers = [c.strip() for c in line.strip().strip("|").split("|")]
        try:
            key_col = headers.index("Jiraキー")
            start_col = headers.index("着手開始日")
        except ValueError:
            return {}
        result = {}
        for row in lines[i + 2:]:
            if not row.strip().startswith("|"):
                break
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) > max(key_col, start_col) and cells[key_col]:
                result[cells[key_col]] = cells[start_col]
        return result
    return {}


def build_markdown(records: list, start_dates: dict) -> str:
    lines = [
        f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "> 識別ルール: Jiraキーが一意識別子。名称はJira summary由来の表示名。旧独自IDは識別に使用しない。",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join(["---"] * len(COLUMNS)) + "|",
    ]
    for rec in sorted(records, key=lambda r: jira_number(r["Jiraキー"])):
        row = [
            rec["Jiraキー"], rec["名称"], rec["状態"], rec["カテゴリ"], rec["担当"],
            rec["後続チケット"], rec["先行チケット"], start_dates.get(rec["Jiraキー"], ""),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    env = load_env(ENV_PATH)
    issues = fetch_issues(env["JIRA_BASE_URL"], env["JIRA_EMAIL"], env["JIRA_API_TOKEN"], env["CURRENT_MILESTONE_EPIC"])
    if not issues:
        fail(f"現行マイルストーン（{env['CURRENT_MILESTONE_EPIC']}）のチケットが0件でした。")
    records = [extract_record(issue) for issue in issues]
    start_dates = parse_existing_start_dates(OUTPUT_PATH)
    OUTPUT_PATH.write_text(build_markdown(records, start_dates), encoding="utf-8")
    print(f"[INFO] {len(records)}件を更新しました: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
