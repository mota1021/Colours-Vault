"""
Jira SPチケットスナップショット生成スクリプト

Colours プロジェクト（Jira: SCRUM）の現行マイルストーンに属するSPチケット
（仕様策定チケット）を Jira REST API (v3) から取得し、
`../チケットスナップショット.md` を冪等に更新する。

正本: 創作/ゲーム/Colours/shared/900.AIエージェント用/Jira_SPチケットスナップショット_実行計画.md

実行方法:
    python jira_sp_snapshot.py
    （または同ディレクトリの run_jira_sp_snapshot.bat）

依存ライブラリ: requests のみ（.env の読み込みは python-dotenv を使わず手動パース）
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import requests

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = Path(r"D:\document\ObsidianVault\.env")
OUTPUT_PATH = SCRIPT_DIR.parent / "チケットスナップショット.md"

REQUIRED_ENV_KEYS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "CURRENT_MILESTONE_EPIC")
COLUMNS = ("ID", "仕様名", "状態", "対応実装チケット", "先行チケット", "着手開始日", "Jiraキー")

SP_LABEL_RE = re.compile(r'^元ID:(SP-\d+)$')
SUMMARY_PREFIX_RE = re.compile(r'^\[SP-\d+\]\s*')
TRAILING_NUMBER_RE = re.compile(r'(\d+)$')

API_TOKEN_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"


# ──────────────────────────────────────────────
# 共通ユーティリティ
# ──────────────────────────────────────────────
def fail(message: str) -> None:
    """エラー内容を標準エラー出力に表示し、非0で異常終了する（サイレント失敗禁止）。"""
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def trailing_number(value: str) -> int:
    """文字列末尾の数字部分を int で返す（'SP-11' → 11、'SCRUM-9' → 9）。数字が無ければ0。"""
    m = TRAILING_NUMBER_RE.search(value)
    return int(m.group(1)) if m else 0


# ──────────────────────────────────────────────
# .env 読み込み（手動パース。python-dotenv 不使用）
# ──────────────────────────────────────────────
def load_env(path: Path) -> dict:
    if not path.exists():
        fail(f".env が見つかりません: {path}")

    env = {}
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            env[key] = value

    missing = [k for k in REQUIRED_ENV_KEYS if not env.get(k)]
    if missing:
        fail(f".env に必要な変数が不足しています（{path}）: {', '.join(missing)}")

    return env


# ──────────────────────────────────────────────
# Jira API 呼び出し
# ──────────────────────────────────────────────
def fetch_all_issues(base_url: str, email: str, api_token: str, milestone_epic: str) -> list:
    """現行マイルストーンのSPチケット全件を取得する（nextPageToken方式でページネーション）。

    旧エンドポイント /rest/api/3/search は410 Goneで廃止済みのため使用しない。
    """
    jql = f'project = SCRUM AND parent = {milestone_epic} AND labels = "分類:仕様策定"'
    url = f"{base_url.rstrip('/')}/rest/api/3/search/jql"
    auth = (email, api_token)
    headers = {"Accept": "application/json"}

    issues = []
    next_page_token = None

    while True:
        params = {
            "jql": jql,
            "fields": "summary,status,labels,issuelinks",
            "maxResults": 100,
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        try:
            resp = requests.get(url, params=params, auth=auth, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            fail(f"Jira APIへの接続に失敗しました: {e}")

        if resp.status_code == 401:
            fail(
                "Jira認証エラー（401 Unauthorized）: APIトークンが無効か期限切れの可能性があります。"
                f" {API_TOKEN_URL} で再発行し、.env の JIRA_API_TOKEN を更新してください。"
            )
        if not resp.ok:
            fail(f"Jira APIがエラーを返しました（HTTP {resp.status_code}）: {resp.text[:500]}")

        try:
            data = resp.json()
        except ValueError:
            fail("Jira APIのレスポンスをJSONとして解析できませんでした。")

        issues.extend(data.get("issues", []))

        if data.get("isLast", True):
            break
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return issues


# ──────────────────────────────────────────────
# issue → レコード変換
# ──────────────────────────────────────────────
def extract_record(issue: dict):
    """1件のissueから ID/仕様名/状態/対応実装チケット/先行チケット/Jiraキー を抽出する。

    `元ID:SP-N` ラベルが無い場合は None を返す（呼び出し側で警告してスキップする）。
    """
    key = issue.get("key", "?")
    fields = issue.get("fields") or {}
    labels = fields.get("labels") or []

    sp_id = None
    for label in labels:
        m = SP_LABEL_RE.match(label)
        if m:
            sp_id = m.group(1)
            break

    if sp_id is None:
        print(f"[WARN] {key}: labelsに『元ID:SP-N』形式が見つからないためスキップします。", file=sys.stderr)
        return None

    summary = fields.get("summary") or ""
    spec_name = SUMMARY_PREFIX_RE.sub("", summary).strip()
    status = (fields.get("status") or {}).get("name", "")

    outward, inward = [], []
    for link in fields.get("issuelinks") or []:
        if (link.get("type") or {}).get("name") != "Blocks":
            continue
        if "outwardIssue" in link:
            outward.append(link["outwardIssue"]["key"])
        if "inwardIssue" in link:
            inward.append(link["inwardIssue"]["key"])

    outward.sort(key=trailing_number)
    inward.sort(key=trailing_number)

    return {
        "ID": sp_id,
        "仕様名": spec_name,
        "状態": status,
        "対応実装チケット": ", ".join(outward) if outward else "-",
        "先行チケット": ", ".join(inward) if inward else "-",
        "Jiraキー": key,
    }


# ──────────────────────────────────────────────
# 既存スナップショットの読み込み（着手開始日のみ保持）
# ──────────────────────────────────────────────
def parse_existing_start_dates(path: Path) -> dict:
    """既存の チケットスナップショット.md を ID 列キーでパースし、着手開始日のみ取り出す。

    他の列（仕様名・状態など）はJira側の最新値で上書きするため保持しない。
    """
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "ID" in stripped and "着手開始日" in stripped:
            header_idx = i
            break

    if header_idx is None:
        return {}

    header_cells = [c.strip() for c in lines[header_idx].strip().strip("|").split("|")]
    try:
        id_col = header_cells.index("ID")
        start_col = header_cells.index("着手開始日")
    except ValueError:
        return {}

    existing = {}
    for line in lines[header_idx + 2:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) <= max(id_col, start_col):
            continue
        row_id = cells[id_col]
        if row_id:
            existing[row_id] = cells[start_col]

    return existing


# ──────────────────────────────────────────────
# テーブル組み立て・書き出し
# ──────────────────────────────────────────────
def build_markdown(records: list, existing_start_dates: dict) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"最終更新: {now_str}", ""]
    lines.append("| " + " | ".join(COLUMNS) + " |")
    lines.append("|" + "|".join(["---"] * len(COLUMNS)) + "|")

    for rec in records:
        start_date = existing_start_dates.get(rec["ID"], "")
        row = [
            rec["ID"], rec["仕様名"], rec["状態"], rec["対応実装チケット"],
            rec["先行チケット"], start_date, rec["Jiraキー"],
        ]
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"


def write_snapshot(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    env = load_env(ENV_PATH)
    issues = fetch_all_issues(
        env["JIRA_BASE_URL"], env["JIRA_EMAIL"], env["JIRA_API_TOKEN"], env["CURRENT_MILESTONE_EPIC"]
    )

    if len(issues) == 0:
        fail(
            f"現行マイルストーン（{env['CURRENT_MILESTONE_EPIC']}）に該当するSPチケットが0件でした。"
            " .env の CURRENT_MILESTONE_EPIC・JQL条件・認証情報を確認してください。"
        )

    records = [r for r in (extract_record(issue) for issue in issues) if r is not None]

    if len(records) == 0:
        fail("取得した全チケットで『元ID:SP-N』ラベルが見つかりませんでした。Jira側のラベル形式を確認してください。")

    records.sort(key=lambda r: trailing_number(r["ID"]))

    existing_start_dates = parse_existing_start_dates(OUTPUT_PATH)

    new_ids = {r["ID"] for r in records}
    existing_ids = set(existing_start_dates.keys())
    added = sorted(new_ids - existing_ids, key=trailing_number)
    updated = sorted(new_ids & existing_ids, key=trailing_number)
    removed = sorted(existing_ids - new_ids, key=trailing_number)

    content = build_markdown(records, existing_start_dates)
    write_snapshot(OUTPUT_PATH, content)

    print(f"[INFO] 取得件数: {len(records)}件（{', '.join(r['ID'] for r in records)}）")
    print(f"[INFO] 追加: {len(added)}件" + (f" （{', '.join(added)}）" if added else ""))
    print(f"[INFO] 更新: {len(updated)}件" + (f" （{', '.join(updated)}）" if updated else ""))
    print(f"[INFO] 削除: {len(removed)}件" + (f" （{', '.join(removed)}）" if removed else ""))
    print(f"[INFO] 出力先: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
