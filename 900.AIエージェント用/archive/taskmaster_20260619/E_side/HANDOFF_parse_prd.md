# 引き継ぎ手順書: TaskMaster `parse_prd`

> **対象**: デスクトップアプリ版 Claude Code で実行すること。CLI 版では動かない（理由は後述）。

---

## やること

TaskMaster の `parse_prd` ツールを使って、PRD ファイルから 13 件のタスクを生成する。

### 実行パラメータ

| パラメータ | 値 |
|---|---|
| `projectRoot` | `E:\UEProjects\Colours` |
| `input` | `E:\UEProjects\Colours\.taskmaster\docs\prd.txt` |
| `numTasks` | `13` |
| `force` | `true`（tasks.json 上書き許可） |

Claude に「parse_prd を実行して」と伝えるだけでも動く。引数を正確に指定したい場合は上記を貼る。

---

## 検証手順（実行後）

1. `mcp__taskmaster-ai__get_tasks` で 13 件のタスクが一覧表示されることを確認
2. `.taskmaster/tasks/tasks.json` が生成されていることを確認
3. タスクのタイトル・説明が日本語になっていることを確認（`responseLanguage: Japanese` に変更済み）

---

## CLI 版で動かない理由

TaskMaster MCP サーバー (v0.43.1) は AI 操作（`parse_prd` / `expand_task` / `update_subtask` 等）を
**MCP sampling**（ホスト側の Claude Code に LLM 呼び出しを代行させる仕組み）に依存している。

CLI 版 Claude Code はこの sampling capability を公開していないため、サーバー起動時に:

```
MCP session missing required sampling capabilities, providers not registered
```

が出て AI プロバイダが未登録になる。その結果 `parse_prd` は実行されてもタスクが生成されない。

デスクトップアプリ版は sampling capability を公開しているため動作する。

---

## フォールバック: それでも動かない場合

デスクトップ版でも失敗したら、CLI の **手動モード**（AI不使用）で1件ずつ登録できる。
`npx task-master-ai add-task --title "タイトル" --description "説明" --details "詳細" --dependencies "依存ID"`
→ PRD の 13 タスク分をループで実行。

---

## 関連ファイル

- PRD: `.taskmaster/docs/prd.txt`（タスク 1〜13 の仕様が記載）
- 設定: `.taskmaster/config.json`（`responseLanguage: Japanese` に変更済み）
