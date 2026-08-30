---
tags: [Colours, AI指示書]
created: 2026-07-06
status: クローズ
---

# タスク管理方針: Jira単一マスター — 決定記録 & 実行指示書

> 2026-07-06 Fable (Claude Code) による方針決定の記録と、Opus/Sonnet 向け実行指示書。
> 発端: `shared/080.個人ページ/Mori/Claudeと一緒にやること.md` 「Taskmaster-aiとJiraを併用するための上手いフローを考える」

## 0. 決定サマリ

- **TaskMaster-ai は不採用**（復活・併用ともに行わない）。タスク管理は **Jira 単一マスター**。
- Claude のタスク読み取りは **RESTスクリプト生成の Markdown スナップショット**（既存 `jira_sp_snapshot.py` パターン）の拡張で賄う。
- Claude からの書き込みが必要な場合のみ **REST write-through スクリプト**を追加する（Phase3・ユーザー要望確認後）。
- 元アイデア「変換スクリプトでトークンゼロ同期」自体は正しい。適用先を Jira↔TaskMaster でなく **Jira↔Markdown** にした形。

### 根拠（要点）

1. **二重マスター問題**: 書き込める台帳が2つあると乖離＝混乱が構造的に発生する。実証: Vault `.taskmaster/tasks/tasks.json`（2026-06-19頃生成・13件）が全件 pending のまま約3週間放置され、現実と乖離済み。
2. **技術ブロッカー**: CLI版 Claude Code は MCP sampling 非対応で、TaskMaster の AI機能（parse_prd / expand 等）が動かない（v0.43.1 で実証。`E:\UEProjects\Colours\.taskmaster\docs\HANDOFF_parse_prd.md` に記録）。
3. **機能は代替済み**: PRD分解→ラフ→020/030/040＋実装計画テンプレ（人間承認付き）／next_task→colours-todo Step3（曜日モード・担当・未決論点・週目標込みで選定）／安価な読み→チケットスナップショット。現行スタックの方がプロジェクト文脈を多く知っている。
4. **文化非互換**: parse_prd は実装詳細を自動補完する（tasks.json の task4 が CMY 実装手順を創作していた）。「数値・内容を勝手に決めない」原則と衝突。
5. **トークン**: MCP 登録だけで毎セッション数十ツール分のスキーマが読み込まれる。撤去自体が恒常的節約。atlassian MCP 無効化（トークン対策）と同じ設計判断。

### 経緯タイムライン

| 時期 | 出来事 |
|---|---|
| 2026-06-18〜19 | Vault側で parse_prd 実行成功。Phase1実装バックログ13件を生成（`.taskmaster/tasks/tasks.json`・.gitignore下） |
| 同時期 | E:側導入は CLI版の MCP sampling 非対応で AI機能が動作せず。`HANDOFF_parse_prd.md`（デスクトップ版での実行手順）が残されたが未完遂 |
| その後 | Jira移行・`jira_sp_snapshot.py`・スキル群・実装ログ体制が整備され、TaskMaster の想定役割を代替 |
| 2026-07-03 | `運用整備タスク一覧.md` 新設時に「TaskMaster連携出力の格納先・初期化未実施」と注記（実態は手動インボックス） |
| 2026-07-06 | 本決定: 不採用・Jira単一マスター化 |

### 運用3原則（A案）

1. **書き込み先は Jira のみ**（人間は Jira UI、Claude は原則書かない。必要になれば Phase3 のスクリプト経由）
2. **Claude の読みは生成スナップショット**（RESTスクリプト→Markdown、トークンゼロ）
3. **同期状態を持たない**（スナップショットは使い捨ての派生物。再生成＝真実）

### 再検討条件（B案）

「長時間の自律実装キュー運用」を始める場合のみ、Jira→ローカル一方向生成の読み取り専用キャッシュとして TaskMaster を再評価する。A案はB案の部分集合であり後から増築可能（無リグレット）。付録のChatGPT調査で「成熟した公式Jira同期＋CLI対応」が確認された場合も再評価材料とする（それでも二重マスター原理の問題は残る）。

---

## 1. 実行ルール（全Phase共通）

- 本指示書の Step は **1タスク=1Step** で実行し、複数タスクをまとめない。
- ファイル削除は Vault CLAUDE.md 憲法に従う: **git追跡済み→削除のみの別コミット**（コメントに削除ファイルの概要）。**未追跡→内容の記録（アーカイブ）を先にコミットしてから削除**。
- `E:\UEProjects\Colours` 側の変更は **dv (Diversion) へのコミットも必須**（git 管理下のパスなら git も）。
- **「STOP→ユーザー確認」箇所は AskUserQuestion で一問一答**してから進む。§5 の確認事項を推測で決めない。

---

## 2. Phase1: 残骸整理（機械的）

### Step 1-1: ラベル修正（4ファイル・各1行）

| ファイル | 修正 |
|---|---|
| `個人計画/運用ガイド.md` L171 | `（TaskMaster 出力）` → `（手動インボックス運用）` |
| `個人計画/ゲーム開発アシスタント.md` L31 | `（TaskMaster連携）` → `（手動インボックス運用）` |
| `shared/040.構造マップ.md` L25 | `・TaskMaster出力` → `・手動インボックス運用` |
| Vault `.claude/skills/colours-review/SKILL.md` L87 | `（TaskMaster連携）` → `（手動運用）` |

行番号は 2026-07-06 時点。ズレていたら `grep -i taskmaster` で特定する。

### Step 1-2: `shared/090.制作進行/運用整備タスク一覧.md` L10 の注記書き換え

現: `> TaskMaster連携出力の格納先として新設(2026-07-03)。TaskMaster自体は初期化未実施のため、当面はインボックスに直接記入する。`
新: `> 手動インボックスとして運用する（2026-07-06決定: TaskMaster連携は不採用。経緯は [[タスク管理方針_Jira単一マスター_指示書]]）。`
（L9 の入口説明行は変更しない）

### Step 1-3: `shared/080.個人ページ/Mori/Claudeと一緒にやること.md` L1-3

Taskmaster 項目を `- [x]` にし、項目末尾（サブ行の後）に1行追記:
`	→ 2026-07-06 決定: 併用不採用・Jira単一マスター（[[タスク管理方針_Jira単一マスター_指示書]]）`

### Step 1-4: Vault `.taskmaster/` 撤去

1. **STOP→ユーザー確認**（§5-1 アーカイブ要否）
2. （アーカイブする場合）`prd.txt`・`tasks.json` を `shared/900.AIエージェント用/archive/taskmaster_20260619/` へ移動し、記録保全としてコミット
3. `D:\document\ObsidianVault\.taskmaster\` を削除（.gitignore 対象＝git 未追跡のため削除自体に git 操作は不要）
4. Vault `.gitignore` の `# Task Master の生成ファイル` 行と `.taskmaster/` 行（L36-37）を削除。続く `.env.example` 行は、Vault 内に `.env.example` が実在するか Glob で確認し、**無ければ**同時に削除、**有れば**残す

### Step 1-5: E:側 `.taskmaster/` 撤去

1. `dv status` で追跡状態を確認（dv の作業ディレクトリに注意: リポジトリ直下で実行しないと動かない）
2. アーカイブ要否は Step 1-4 の回答に準ずる。`HANDOFF_parse_prd.md` は「CLI版で動かない理由」の技術記録として Vault アーカイブ（Step 1-4 と同じフォルダ）へ移すことを推奨
3. `E:\UEProjects\Colours\.taskmaster\` を削除し、dv commit（git 管理下なら git も）

### Step 1-6: taskmaster-ai MCP 登録解除

1. `claude mcp list` で登録スコープを確認
2. `claude mcp remove taskmaster-ai`（スコープ指定が必要なら付与）
3. `E:\UEProjects\Colours\.claude\settings.local.json` の `permissions.allow` から `mcp__taskmaster-ai__get_tasks`・`mcp__taskmaster-ai__parse_prd` の2行を削除

### Step 1-7: `E:\UEProjects\Colours\.env` 整理

**STOP→ユーザー確認**（§5-2）。`PERPLEXITY_API_KEY` は TaskMaster research 用の可能性が高いが、他用途の有無を確認してから行削除（またはファイルごと削除）を決める。

### Step 1-8: 検証とコミット

1. Vault・E: 双方で `grep -ri taskmaster` を実行し、アクティブ文書にヒットが無いことを確認（archive/・デイリーノート/・Reports/・実装ログ等の履歴系は残ってよい）
2. `/mcp` に taskmaster-ai が表示されないことを確認
3. git（Vault）・dv（E:）にコミット

---

## 3. Phase2: スナップショット拡張（要件インタビュー→実装）

目的: colours-todo Step3 が実装チケット（CS/PL/EW/FL/SD/GL/MB/LV/GE）についても「スナップショット→無ければ口頭確認」で回るようにし、口頭確認への依存を減らす。

### Step 2-1: STOP→要件インタビュー（§5-3〜5-6 を一問一答）

Jira 上の実装チケットの実態（カテゴリの持ち方・「前提:」依存リンクの表現方法・対象マイルストーンの範囲）もここで確認する。

### Step 2-2: スクリプト実装

`shared/.vault-data/900.AIエージェント用/scripts/jira_sp_snapshot.py` を拡張（§5-4 の回答により姉妹スクリプトの場合あり）。既存設計を踏襲する:
- 認証・env 構成（`JIRA_API_TOKEN`・`CURRENT_MILESTONE_EPIC`）
- サイレント失敗しないエラー設計（401 案内・0件時の案内）
- ユーザー管理列（着手開始日相当）は上書きせず保持、他列は冪等上書き

### Step 2-3: スキル更新

- Vault `.claude/skills/colours-todo/SKILL.md` Step 3 の「Jira参照手段」を新スナップショット範囲に合わせて更新
- `.claude/skills/colours-sp-snapshot/SKILL.md` に影響があれば整合させる

### Step 2-4: 実データで生成→内容確認→ユーザー報告→コミット

---

## 4. Phase3（任意）: write-through スクリプト

### Step 3-1: STOP→ユーザー確認（§5-7）

Claude が Jira ステータスを直接更新する必要が実際にあるか。**不要なら Phase3 は実施しない。**

### Step 3-2: 必要な場合のみ実装

`jira_task_update.py`（引数: チケットキー・遷移先ステータス・任意コメント）を `scripts/` に追加。同期状態を持たない write-through 設計（1回の呼び出し=1回のREST更新）。スキル（colours-review / colours-end 等）への組み込みは別途ユーザー合意を得る。

---

## 5. ユーザーへの確認事項（一問一答・該当Stepで聞く）

1. Vault `tasks.json` / `prd.txt` をアーカイブしてから削除するか、そのまま削除するか（推奨: アーカイブ。2026-06-19時点のPhase1バックログの歴史記録のため）
2. E: `.env` の `PERPLEXITY_API_KEY` に TaskMaster research 以外の用途があるか
3. スナップショット拡張の対象範囲: 現行マイルストーンの実装チケットのみか、SP含む全チケット統合か
4. 出力先: 既存 `チケットスナップショット.md` に統合するか、実装チケット用の別ファイルにするか（スクリプト拡張か姉妹スクリプトかもここで決まる）
5. スナップショットに必要なフィールド（状態・担当・前提のほかに何が要るか）
6. 新ファイル／新スクリプトの命名
7. Claude から Jira への書き込み（ステータス遷移）を実際に必要としているか
8. （備考）Vault に登録が残る Linear MCP（Jira移行済みで未使用の可能性・トークン節約）も解除するか

---

## 6. 完了条件

- Phase1: Step 1-8 の検証がパスし、git（Vault）・dv（E:）両方にコミット済み
- Phase2: 実装チケットがスナップショット経由で colours-todo から参照できる
- 各Phase完了時に本指示書冒頭の `status` を更新（Phase1完了 → Phase2完了 → クローズ）

---

## 付録: ChatGPT 検証プロンプト（鮮度ヘッジ・任意）

> 実行は任意。回答が「成熟した公式Jira同期＋CLI対応あり」の場合のみ §0 再検討条件に従いB案を再評価。それ以外は本指示書のまま進める。

```
【調査依頼】AIエージェント用タスク管理OSS「Task Master AI」(eyaltoledano/claude-task-master,
npm: task-master-ai) の2026年7月時点の最新状況を、出典URL付きで教えてください。
背景: UE5開発でJira(SCRUM)を人間用タスク管理に使用中。Claude Code CLIとの連携を検討したが、
(1) v0.43.1のMCPサーバーはAI機能(parse_prd等)がMCP sampling依存でCLI版では動作しない
(2) Jiraとの二重管理・同期保守コストの懸念、の2点で不採用方針。これを覆す材料の有無を確認したい。
質問:
1. 最新版にJiraとの公式連携(インポート/双方向同期)は実装されたか。成熟度は？
2. CLI版Claude Code(sampling非対応ホスト)でもAI機能が動くようになったか？
3. Jira⇄tasks.json同期の実績あるサードパーティOSSはあるか？
4. 総合判定: 「Jira単一マスター+自作RESTスナップショットスクリプト」運用と比べ、
   最新版TaskMasterを併用する積極的理由はあるか？
```
