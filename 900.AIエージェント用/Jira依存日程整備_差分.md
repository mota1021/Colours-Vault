最終生成: 2026-07-05 11:48（read-only計算・Jira未適用）

# Jira 依存関係・作業日程 整備差分

> 生成: `scripts/jira_dep_schedule_plan.py`（Jira書込なし）。適用は Vault セッションの Atlassian MCP で行う（末尾の手順参照）。
> パラメータ: 起点=2026-07-06 / 締切=2026-12-20 / 稼働 Mori 7.0h·Hiruta 3.0h/週 / 実装4h·配置2h

## 1. 依存リンク差分

### 追加（39件） — 先行 → 被依存（先行が blocks / 被依存が is blocked by）

| # | 先行(blocker) | 被依存(blocked) |
|---|---|---|
| 1 | CS-1 (SCRUM-10) | CS-2 (SCRUM-11) |
| 2 | PL-3 (SCRUM-15) | PL-4 (SCRUM-16) |
| 3 | PL-3 (SCRUM-15) | PL-5 (SCRUM-17) |
| 4 | PL-2 (SCRUM-14) | PL-6 (SCRUM-18) |
| 5 | CS-1 (SCRUM-10) | FL-1 (SCRUM-24) |
| 6 | PL-2 (SCRUM-14) | FL-1 (SCRUM-24) |
| 7 | FL-1 (SCRUM-24) | FL-2 (SCRUM-25) |
| 8 | SD-1 (SCRUM-26) | SD-2 (SCRUM-27) |
| 9 | SD-1 (SCRUM-26) | SD-3 (SCRUM-28) |
| 10 | SD-1 (SCRUM-26) | SD-4 (SCRUM-29) |
| 11 | SD-3 (SCRUM-28) | SD-4 (SCRUM-29) |
| 12 | GL-1 (SCRUM-30) | GL-2 (SCRUM-31) |
| 13 | GL-1 (SCRUM-30) | GL-3 (SCRUM-32) |
| 14 | GL-2 (SCRUM-31) | GL-3 (SCRUM-32) |
| 15 | EW-1 (SCRUM-19) | MB-2 (SCRUM-34) |
| 16 | MB-1 (SCRUM-33) | MB-2 (SCRUM-34) |
| 17 | MB-1 (SCRUM-33) | MB-4 (SCRUM-38) |
| 18 | MB-2 (SCRUM-34) | MB-4 (SCRUM-38) |
| 19 | MB-3a (SCRUM-35) | MB-4 (SCRUM-38) |
| 20 | MB-3b (SCRUM-36) | MB-4 (SCRUM-38) |
| 21 | MB-3c (SCRUM-37) | MB-4 (SCRUM-38) |
| 22 | PL-1 (SCRUM-13) | LV-1 (SCRUM-39) |
| 23 | PL-3 (SCRUM-15) | LV-2 (SCRUM-40) |
| 24 | EW-5 (SCRUM-20) | LV-3 (SCRUM-41) |
| 25 | CS-3 (SCRUM-12) | LV-4 (SCRUM-42) |
| 26 | EW-5 (SCRUM-20) | LV-4 (SCRUM-42) |
| 27 | EW-4 (SCRUM-23) | LV-4 (SCRUM-42) |
| 28 | SD-4 (SCRUM-29) | LV-5 (SCRUM-43) |
| 29 | FL-2 (SCRUM-25) | LV-6 (SCRUM-44) |
| 30 | GL-3 (SCRUM-32) | LV-7 (SCRUM-45) |
| 31 | MB-4 (SCRUM-38) | LV-8 (SCRUM-46) |
| 32 | EW-2 (SCRUM-21) | LV-9 (SCRUM-47) |
| 33 | MB-2 (SCRUM-34) | LV-9 (SCRUM-47) |
| 34 | EW-2 (SCRUM-21) | LV-10 (SCRUM-48) |
| 35 | SD-1 (SCRUM-26) | LV-10 (SCRUM-48) |
| 36 | EW-4 (SCRUM-23) | MVP-LV (SCRUM-50) |
| 37 | PL-3b (SCRUM-68) | MVP-LV (SCRUM-50) |
| 38 | MVP-LV (SCRUM-50) | MVP-GE (SCRUM-51) |
| 39 | PL-3 (SCRUM-15) | PL-3b (SCRUM-68) |

### 削除（38件） — 設計外の誤リンク

| # | 先行 | 被依存 | linkId(REST削除用) |
|---|---|---|---|
| 1 | CS-2 (SCRUM-11) | CS-1 (SCRUM-10) | 10116 |
| 2 | FL-1 (SCRUM-24) | CS-1 (SCRUM-10) | 10120 |
| 3 | LV-4 (SCRUM-42) | CS-3 (SCRUM-12) | 10140 |
| 4 | LV-1 (SCRUM-39) | PL-1 (SCRUM-13) | 10137 |
| 5 | PL-6 (SCRUM-18) | PL-2 (SCRUM-14) | 10119 |
| 6 | FL-1 (SCRUM-24) | PL-2 (SCRUM-14) | 10121 |
| 7 | PL-4 (SCRUM-16) | PL-3 (SCRUM-15) | 10117 |
| 8 | PL-5 (SCRUM-17) | PL-3 (SCRUM-15) | 10118 |
| 9 | LV-2 (SCRUM-40) | PL-3 (SCRUM-15) | 10138 |
| 10 | PL-3b (SCRUM-68) | PL-3 (SCRUM-15) | 10153 |
| 11 | MVP-LV (SCRUM-50) | PL-3b (SCRUM-68) | 10152 |
| 12 | MB-2 (SCRUM-34) | EW-1 (SCRUM-19) | 10130 |
| 13 | LV-3 (SCRUM-41) | EW-5 (SCRUM-20) | 10139 |
| 14 | LV-4 (SCRUM-42) | EW-5 (SCRUM-20) | 10141 |
| 15 | LV-9 (SCRUM-47) | EW-2 (SCRUM-21) | 10147 |
| 16 | LV-10 (SCRUM-48) | EW-2 (SCRUM-21) | 10149 |
| 17 | LV-4 (SCRUM-42) | EW-4 (SCRUM-23) | 10142 |
| 18 | MVP-LV (SCRUM-50) | EW-4 (SCRUM-23) | 10151 |
| 19 | FL-2 (SCRUM-25) | FL-1 (SCRUM-24) | 10122 |
| 20 | LV-6 (SCRUM-44) | FL-2 (SCRUM-25) | 10144 |
| 21 | SD-2 (SCRUM-27) | SD-1 (SCRUM-26) | 10123 |
| 22 | SD-3 (SCRUM-28) | SD-1 (SCRUM-26) | 10124 |
| 23 | SD-4 (SCRUM-29) | SD-1 (SCRUM-26) | 10125 |
| 24 | LV-10 (SCRUM-48) | SD-1 (SCRUM-26) | 10150 |
| 25 | SD-4 (SCRUM-29) | SD-3 (SCRUM-28) | 10126 |
| 26 | LV-5 (SCRUM-43) | SD-4 (SCRUM-29) | 10143 |
| 27 | GL-2 (SCRUM-31) | GL-1 (SCRUM-30) | 10127 |
| 28 | GL-3 (SCRUM-32) | GL-1 (SCRUM-30) | 10128 |
| 29 | GL-3 (SCRUM-32) | GL-2 (SCRUM-31) | 10129 |
| 30 | LV-7 (SCRUM-45) | GL-3 (SCRUM-32) | 10145 |
| 31 | MB-2 (SCRUM-34) | MB-1 (SCRUM-33) | 10131 |
| 32 | MB-4 (SCRUM-38) | MB-1 (SCRUM-33) | 10132 |
| 33 | MB-4 (SCRUM-38) | MB-2 (SCRUM-34) | 10133 |
| 34 | LV-9 (SCRUM-47) | MB-2 (SCRUM-34) | 10148 |
| 35 | MB-4 (SCRUM-38) | MB-3a (SCRUM-35) | 10134 |
| 36 | MB-4 (SCRUM-38) | MB-3b (SCRUM-36) | 10135 |
| 37 | MB-4 (SCRUM-38) | MB-3c (SCRUM-37) | 10136 |
| 38 | LV-8 (SCRUM-46) | MB-4 (SCRUM-38) | 10146 |

### ⚠️ 要確認リンク（3件） — 非元ID(SCRUM-53等)による block。自動削除せず判断を仰ぐ

| 先行(key) | 被依存 | linkId | 備考 |
|---|---|---|---|
| SCRUM-53 | CS-1 (SCRUM-10) | 10021 | 移行検証用テストチケットの疑い（Step6でSCRUM-53検証） |
| SCRUM-53 | CS-2 (SCRUM-11) | 10022 | 移行検証用テストチケットの疑い（Step6でSCRUM-53検証） |
| SCRUM-53 | CS-3 (SCRUM-12) | 10023 | 移行検証用テストチケットの疑い（Step6でSCRUM-53検証） |

- 再構成後DAG循環チェック: OK（循環なし）

## 2. 開始日/期限の差分（本格再計算・変更行のみ）

| 元ID | key | レーン | 旧開始→新開始 | 旧期限→新期限 | 工数 |
|---|---|---|---|---|---|

- 依存整合（先行期限 < 被依存開始）違反: 0件

## 3. エピック期限の差分

| エピック | M | 旧開始 | 旧期限 | 新開始 | 新期限 |
|---|---|---|---|---|---|
| SCRUM-5 | M1/MVP | 2026-07-06 | 2026-08-05 | 2026-07-06 | 2026-08-05 |
| SCRUM-6 | M2 | 2026-07-31 | 2026-08-24 | 2026-07-31 | 2026-08-24 |
| SCRUM-7 | M3 | 2026-08-14 | 2026-10-23 | 2026-08-14 | 2026-10-23 |
| SCRUM-8 | M4 | 2026-10-24 | 2026-12-07 | 2026-10-24 | 2026-12-07 |
| SCRUM-9 | M5 | 2026-11-19 | 2026-11-22 | 2026-11-19 | 2026-11-22 |

## 4. 容量レポート（重要）

- MVP（MVP-LV/MVP-GE）完了: **2026-08-05**（目安 2026-08-02 → ⚠️超過）
- レーン最終完了: Mori **2026-11-22** / Hiruta **2026-12-07**
- ステージ1締切 2026-12-20 超過: **0件**

## 5. 要確認（勝手に確定しない事項）

- **レーン競合**: 010原案の担当と2026-07-03ロードマップのレーン割りが食い違う → ロードマップ(新)採用で計算: PL-6, SD-2, EW-3, GE-1。
- **稼働→暦日換算**: Mori 7h/週=1.0h/日・Hiruta 3h/週≈0.43h/日（暦日ベース・週末含む）。実働が平日集中なら要調整。
- **起点2026-07-06**・凍結(CS-1/EW-1/PL-2 完了扱い)前提。
- **SP(仕様策定)チケットは稼働非消費**で計算（多くは完了）。未完SPが先行にある実装は着手前にSP完了が必要。

## 適用手順（Vault セッション / Atlassian MCP）

1. **リンク追加**: 各行、先行チケットに『blocks → 被依存』の Blocks リンクを作成。
2. **リンク削除**: linkId 指定で削除（MCPに削除がなければ REST `DELETE /rest/api/3/issueLink/{linkId}` か UI）。
3. **日付更新**: 各 key の `customfield_10015`(開始日) と `duedate`(期限) を新値に更新。
4. **エピック期限**: SCRUM-5〜9 の開始/期限を §3 の新値に更新。
5. 適用後、タイムラインで依存線・バー長・順序を目視確認。
