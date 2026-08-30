"""
Jira チケット write-through 更新スクリプト（Phase3）

Colours プロジェクト（Jira: SCRUM）の指定チケットのステータスを遷移させ、
同時にコメントを1件追加する。Claude からの唯一の Jira 書き込み経路。

同期状態を持たない write-through 設計: 1回の呼び出し = 1回の REST 更新（transition + comment を
1リクエストに束ねる）。ローカルにキャッシュや対応表は持たない。

正本: 創作/ゲーム/Colours/shared/900.AIエージェント用/タスク管理方針_Jira単一マスター_指示書.md Phase3

実行方法:
    python jira_task_update.py <ISSUE_KEY> <TRANSITION_NAME> <COMMENT>

例:
    python jira_task_update.py SCRUM-14 進行中 "実装着手"
    python jira_task_update.py SCRUM-14 完了 "PIE検証完了・マージ済み"

引数:
    ISSUE_KEY       例: SCRUM-14
    TRANSITION_NAME 遷移先を示す名前。Jira側の transition.name（例: "進行中"）または
                    遷移先ステータス名 transition.to.name のどちらでも一致すればよい。
                    一致しない場合はそのチケットで実際に選べる遷移一覧を表示して終了する。
    COMMENT         必須。空文字は不可（遷移理由を残さない運用は許可しない）。

依存ライブラリ: requests のみ（.env の読み込みは python-dotenv を使わず手動パース）
"""

import sys
from pathlib import Path

import requests

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
ENV_PATH = Path(r"D:\document\ObsidianVault\.env")
REQUIRED_ENV_KEYS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
API_TOKEN_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"


# ──────────────────────────────────────────────
# 共通ユーティリティ（jira_sp_snapshot.py と同型・本スクリプト単体で完結させる）
# ──────────────────────────────────────────────
def fail(message: str) -> None:
    """エラー内容を標準エラー出力に表示し、非0で異常終了する（サイレント失敗禁止）。"""
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


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


def comment_adf(text: str) -> dict:
    """プレーンテキストを Jira REST v3 が要求する ADF (Atlassian Document Format) に変換する。"""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
        ],
    }


# ──────────────────────────────────────────────
# Jira API 呼び出し
# ──────────────────────────────────────────────
def fetch_transitions(base_url: str, auth: tuple, issue_key: str) -> list:
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, auth=auth, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        fail(f"Jira APIへの接続に失敗しました: {e}")

    if resp.status_code == 401:
        fail(
            "Jira認証エラー（401 Unauthorized）: APIトークンが無効か期限切れの可能性があります。"
            f" {API_TOKEN_URL} で再発行し、.env の JIRA_API_TOKEN を更新してください。"
        )
    if resp.status_code == 404:
        fail(f"チケットが見つかりません（404）: {issue_key}。キーの綴りを確認してください。")
    if not resp.ok:
        fail(f"Jira APIがエラーを返しました（HTTP {resp.status_code}）: {resp.text[:500]}")

    try:
        data = resp.json()
    except ValueError:
        fail("Jira APIのレスポンスをJSONとして解析できませんでした。")

    return data.get("transitions", [])


def resolve_transition_id(transitions: list, transition_name: str, issue_key: str) -> str:
    """transition.name または transition.to.name のどちらかと完全一致するものを探す。

    見つからない場合は現在選べる遷移一覧を表示して異常終了する。
    """
    for t in transitions:
        if t.get("name") == transition_name:
            return t["id"]
        if (t.get("to") or {}).get("name") == transition_name:
            return t["id"]

    available = [f"{t.get('name')}（遷移先: {(t.get('to') or {}).get('name')}）" for t in transitions]
    fail(
        f"{issue_key} では遷移 '{transition_name}' を選べません。"
        f" 現在選べる遷移: {', '.join(available) if available else '(なし)'}"
    )


def apply_transition_with_comment(base_url: str, auth: tuple, issue_key: str, transition_id: str, comment: str) -> None:
    """transition と comment を1リクエストにまとめてPOSTする（write-through: 1呼び出し=1更新）。"""
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    body = {
        "transition": {"id": transition_id},
        "update": {
            "comment": [
                {"add": {"body": comment_adf(comment)}}
            ]
        },
    }

    try:
        resp = requests.post(url, json=body, auth=auth, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        fail(f"Jira APIへの接続に失敗しました: {e}")

    if resp.status_code == 401:
        fail(
            "Jira認証エラー（401 Unauthorized）: APIトークンが無効か期限切れの可能性があります。"
            f" {API_TOKEN_URL} で再発行し、.env の JIRA_API_TOKEN を更新してください。"
        )
    if resp.status_code == 400:
        fail(f"Jira APIが不正なリクエストと判定しました（400）: {resp.text[:500]}")
    if resp.status_code not in (200, 204):
        fail(f"Jira APIがエラーを返しました（HTTP {resp.status_code}）: {resp.text[:500]}")


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if len(sys.argv) != 4:
        fail(
            "使い方: python jira_task_update.py <ISSUE_KEY> <TRANSITION_NAME> <COMMENT>\n"
            '例: python jira_task_update.py SCRUM-14 進行中 "実装着手"'
        )

    issue_key, transition_name, comment = sys.argv[1], sys.argv[2], sys.argv[3]
    if not comment.strip():
        fail("COMMENT は必須です（空文字は不可）。遷移理由を必ず添えてください。")

    env = load_env(ENV_PATH)
    base_url = env["JIRA_BASE_URL"].rstrip("/")
    auth = (env["JIRA_EMAIL"], env["JIRA_API_TOKEN"])

    transitions = fetch_transitions(base_url, auth, issue_key)
    if not transitions:
        fail(f"{issue_key} には現在選べる遷移がありません（権限またはワークフロー設定を確認してください）。")

    transition_id = resolve_transition_id(transitions, transition_name, issue_key)
    apply_transition_with_comment(base_url, auth, issue_key, transition_id, comment)

    print(f"[INFO] {issue_key} を '{transition_name}' へ遷移し、コメントを追加しました。")
    print(f"[INFO] コメント: {comment}")


if __name__ == "__main__":
    main()
