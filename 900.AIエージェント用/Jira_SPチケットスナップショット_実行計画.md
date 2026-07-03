# Jira SPチケット確認スクリプト — API初期設定とスクリプト計画

## Context

`創作/ゲーム/Colours/shared/080.個人ページ/Mori/Claudeと一緒にやること.md` の2番目の項目「SPチケットを一緒に作業する際は、作業開始時にJiraから仕様名・状態・対応実装チケットを確認し、リストに転記してスナップショットを更新する」を自動化したい。

検討の結果、以下を決定済み:
- 自動起動の仕組みは**スキル**（フックではない。フックはツール実行イベント起点のため会話上の意図を検知できない）
- Jira連携は**MCPではなくREST APIを直接呼ぶPythonスクリプト**にする。MCP経由だと検索結果をそのまま会話に流すぶんトークンを消費するのに対し、スクリプトなら処理を会話コンテキスト外で完結でき、Claude Code以外（バッチファイル・タスクスケジューラ）からも実行できる
- Jira Cloud REST APIは既存のAtlassian契約内で追加費用なく使えるが、APIトークンはプログラムから自動更新できず期限切れ前に手動再発行が必要（調査済み）という制約は許容する

**このセッションのスコープは「APIの初期設定」と「スクリプトの計画（要件・処理ステップ）」までに限定する。** スキル本体（`game-sp-snapshot`）、`チケットスナップショット.md` の雛形作成、`Claudeと一緒にやること.md` の更新は次回以降の作業とする。

## 決定事項（ユーザー確認済み・スクリプトに関わるもの）

- 実行言語: Python（`requests` は環境に導入済みと確認済み）
- APIトークン保存場所: Vaultルートの `D:\document\ObsidianVault\.env`（`.gitignore` で既に除外済み）
- 出力先（将来作成予定）: `創作/ゲーム/Colours/shared/900.AIエージェント用/チケットスナップショット.md`
- 記録項目: `ID / 仕様名 / 状態 / 対応実装チケット / 先行チケット / 着手開始日 / Jiraキー`
- 対象範囲: 現在のマイルストーンのSPチケットのみ

## 1. API初期設定（完了済み・2026-07-03確認）

`D:\document\ObsidianVault\.env` に以下の4変数が設定済みであることを確認した:

```
JIRA_BASE_URL=https://<サイト名>.atlassian.net
JIRA_EMAIL=<Atlassianログインメール>
JIRA_API_TOKEN=<id.atlassian.comで発行したAPIトークン>
CURRENT_MILESTONE_EPIC=SCRUM-5
```

APIトークンの再発行が必要になった場合は https://id.atlassian.com/manage-profile/security/api-tokens で発行する（ユーザー操作、Claudeは代行不可）。
マイルストーンが進んだら（M1→M2等）、`CURRENT_MILESTONE_EPIC` の値を手動で更新する。

### 使用エンドポイント（重要）

**`/rest/api/3/search` は廃止済み（HTTP 410 Gone、2026-07-03実測）。`/rest/api/3/search/jql` を使うこと。** 新エンドポイントは旧版と以下の点で挙動が異なる:
- `fields` パラメータを明示指定しないと `key` すら返さない（`fields=summary,status,labels,issuelinks` を指定する）
- ページネーションは `startAt`/`total` 方式ではなく `nextPageToken`/`isLast` 方式

### 疎通確認結果（2026-07-01実施・確定）

`GET {JIRA_BASE_URL}/rest/api/3/issue/SCRUM-54`（SP-1）で実データを確認し、以下を確定した:

| 項目 | Jira側フィールド | 例 |
|---|---|---|
| SP-ID | `labels` 内の `元ID:SP-1` 形式 | `元ID:SP-1` |
| 仕様名 | `summary` の `[SP-1] ` プレフィックスを除いた部分 | `消える壁 仕様策定` |
| 状態 | `status.name` | `完了` |
| Jiraキー | `key` | `SCRUM-54` |
| 現在のマイルストーン | `parent`（Epic Link）。現在は `.env` の `CURRENT_MILESTONE_EPIC` で固定値管理 | `SCRUM-5`（M1 MVP） |
| 対応実装チケット | `issuelinks` のうち `type.name == "Blocks"` かつ `outwardIssue` を持つもの（このSPが実装側をブロックしている＝実装が待っている） | `SCRUM-19, SCRUM-21, SCRUM-22, SCRUM-23` |
| 先行チケット | `issuelinks` のうち `type.name == "Blocks"` かつ `inwardIssue` を持つもの（このSPが逆にブロックされている側）。`type.name` の条件を外すと Blocks 以外のリンク種別を誤検出するため必須。SP-1では0件だったが構造は確認済み | - |

**JQL（確定）**: `project = SCRUM AND parent = {CURRENT_MILESTONE_EPIC} AND labels = "分類:仕様策定"`

2026-07-03に `/rest/api/3/search/jql` で実行し動作確認済み。4件ヒット（SP-1, SP-4, SP-7, SP-11）、`isLast=true`、対応実装チケット・先行チケットのリンク構造も期待通りだった。

## 2. スクリプト要件リスト

`創作/ゲーム/Colours/shared/900.AIエージェント用/scripts/jira_sp_snapshot.py`（次回作成予定）に対する要件:

1. **認証**: `.env` から `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` を読み込み、Basic認証でJira REST API v3にアクセスする。`.env` の読み込みは python-dotenv に依存せず手動パースする（`KEY=VALUE` 形式を1行ずつ分割。依存ライブラリを `requests` のみに保つ。2026-07-03の検証スクリプトで実証済みの方式）。
2. **対象データ**: Colours プロジェクト（SCRUM）のうち、現在のマイルストーンに属するSPチケットのみを取得する（絞り込み条件は §1 の疎通確認で確定した内容を使う）。エンドポイントは `/rest/api/3/search/jql`（旧 `/search` は410で使用不可）。`fields=summary,status,labels,issuelinks` を必ず明示指定する（未指定だと `key` すら返らない）。
3. **取得・整形項目**: `ID(SP番号) / 仕様名(summary) / 状態(status.name) / 対応実装チケット / 先行チケット / Jiraキー` を抽出する。対応実装チケット・先行チケットはいずれも `issuelinks` のうち `type.name == "Blocks"` のものに限定し、前者は `outwardIssue`、後者は `inwardIssue` を持つものとする。
4. **既存データの保持**: 出力先ファイルに既存の「着手開始日」列があれば、Jira側にはない情報のため上書きせず保持する。
5. **冪等性**: 何度実行しても安全な結果になること（既存行は上書き、新規SPチケットは追加、対象マイルストーン外になった行は削除）。
6. **実行手段**: スクリプト単体実行に加えて、`run_jira_sp_snapshot.bat`（`python jira_sp_snapshot.py` を呼ぶだけの薄いラッパー）を用意し、Claude Codeを介さずタスクスケジューラや手動実行でも動かせるようにする。
7. **エラー処理**: 認証失敗（401）・APIトークン期限切れ・対象0件のケースで、原因が分かるメッセージを出して異常終了する（サイレント失敗させない）。
8. **ページネーション**: レスポンスの `isLast` が `true` になるまで `nextPageToken` を渡してループし、全件取得する（現在は4件だがSPチケット増加に備える）。
9. **エンコーディング**: 出力mdの読み書きは `encoding='utf-8'` を明示する（Windows既定のcp932による文字化け防止。2026-07-03の検証時にコンソール出力で文字化けを実際に確認済み）。
10. **最終更新日時**: スナップショットmdのテーブル上部に「最終更新: YYYY-MM-DD HH:MM」の1行を出力し、実行のたびに更新する（データの鮮度を判別できるようにする）。

## 3. 処理の計画（スクリプト内の処理ステップ）

1. Vaultルートの `.env` を手動パースで読み込み、4つの環境変数を取得する。未設定ならエラー終了。
2. §1で確定したJQLで `/rest/api/3/search/jql` を呼び（`fields=summary,status,labels,issuelinks` を明示指定）、現行マイルストーンのSPチケット一覧を取得する。`isLast` が `true` になるまで `nextPageToken` でループして全件集める。
3. レスポンスの各issueから `ID / 仕様名 / 状態 / 対応実装チケット / 先行チケット / Jiraキー` を抽出する。
4. 出力先 `チケットスナップショット.md` が既に存在する場合は読み込み、既存テーブルをID列をキーにパースする（存在しない場合は空テーブルとして扱う）。
5. Jiraから取得した内容で各行をマージする: 既存行は`仕様名/状態/対応実装チケット/先行チケット/Jiraキー`を上書きし`着手開始日`は保持、新規行は追加（`着手開始日`は空欄）、現行マイルストーンに存在しなくなった行は削除する。
6. マージ後のテーブルを「最終更新: YYYY-MM-DD HH:MM」の行とともにMarkdown形式で書き戻す（UTF-8明示）。
7. 実行結果（取得件数・追加/更新/削除件数）を標準出力にログとして出す。

## 検証方法

1. ~~`.env` にJira認証情報を設定し、疎通確認用のテスト呼び出し（§1）を1回実行してフィールド構成を確認する。~~ → **完了済み（2026-07-03）**。`.env` 設定・エンドポイント確定・JQL動作確認まで済み。
2. スクリプト実装後、単体実行して `チケットスナップショット.md`（テスト用の空ファイルを用意）が要件通りに更新されることを確認する。
3. 2回目実行しても結果が変わらない（冪等）ことを確認する。
