# Colours プロジェクト UE5.3 → UE5.8 移行計画

## Context（背景）

Colours（`E:\UEProjects\Colours`）は現在 **UE5.3 / C++** で開発中。以下の事情で 5.8 へ移行する。

1. **Diversion が UE5.8 を公式サポート**（Epic 公式ドキュメントに 5.8 版の Diversion 節あり／FAB に 5.8 対応プラグイン）。これが移行の最後のブロッカー解消 =「対応が来た」。
2. **既にビルド環境の不一致が発生済み**：CS-3 実装（[[260705.CS-3照合判定関数]]）のビルド時、`.uproject`/`Target.cs` は 5.3 向けだが UnrealBuildTool が **UE5.8系**を呼んでしまい設定不一致エラー（`"Colours has build products in common with UnrealGame"`）。手動ビルドは通過済みだが未解決課題として [[Claudeと一緒にやること]] / [[070.020.現在地|現在地]] に記録。→ マシンには 5.8 系ツールが既に存在する可能性が高い。

**目標**：エンジンを 5.8 に正式移行し、C++ ビルド・アセット・レベルを 5.8 で健全化。ビルド環境不一致を根本解決し、Vault/プロジェクト文書を 5.8 に更新する。**本タスクのゴールは「計画書の作成」まで**（実行は別途）。

---

## 現状インベントリ（Explore 調査結果）

| 項目 | 内容 |
|---|---|
| エンジン | UE5.3（`Colours.uproject` の `EngineAssociation: "5.3"`）|
| C++モジュール | 単一 game module `Colours`（Runtime）。11 cpp / 11 h。Public/Private split |
| Build.cs 依存 | Public: `Core, CoreUObject, Engine, InputCore, EnhancedInput, GeometryFramework, GeometryScriptingCore, GeometryCore, DynamicMesh` / Private: なし |
| Target.cs | `DefaultBuildSettings = V4`、`IncludeOrderVersion = Unreal5_3`（Game/Editor 両方同一）|
| カスタムプラグイン | `VisualStudioTools`（MS製・v2.8・**EngineVersion 未記載**・C++ソースあり）1本のみ |
| 有効な engine プラグイン | ModelingToolsEditorMode, GeometryScripting, VisualStudioTools, CommonUI, **Diversion** |
| Config | `DefaultEngine.ini`（16.6KB・レンダラ/RHI設定）, DefaultGame/Input/Editor 他 |
| Content | 約 **1GB**・**492 uasset / 6 umap**。**OFPA使用**（`__ExternalActors__` / `__ExternalObjects__`）。大半は StarterContent/ThirdPerson テンプレ |
| VCS | **Diversion のみ**（`.git` なし）。`.dvignore` で **`Content/**` と `Binaries/` を追跡**。ヒルタがバイナリを dv 経由で同期 |
| 高リスク箇所 | **Geometry系モジュール**（GeometryScripting API は 5.3→5.8 で変化大）・EnhancedInput・レンダラ既定値 |

---

## 決定事項（ユーザー確認済み 2026-07-06）

- **dv ブランチ戦略**：**移行用ブランチを切る**。main は 5.3 のまま残し、専用ブランチで作業・検証。ビルド通過＋プレイ確認後に main へマージ。ヒルタは検証完了まで 5.3 で作業継続可。
- **スコープ**：UE プロジェクト移行 **＋ Vault/プロジェクト文書の更新**まで含む。
- **バックアップ**：**Diversion のバージョン履歴のみに依存**（別途フォルダ複製はしない）。

---

## 移行手順

### Phase 0 — 事前環境確認（Claude 調査 + ユーザー操作）
- [x] **UE5.8 のインストール確認**：Epic Games Launcher に 5.8 があるか。無ければユーザーがインストール。インストール先パスを確定（UBT 不一致調査で「Program Files 配下に 5.3 が見つからない」と記録あり → 実体パスを特定）。 ✅ 2026-07-08
- [x] **Visual Studio ツールチェーン確認**：5.8 が要求する VS2022 / MSVC バージョン・Windows SDK が入っているか。不足ならユーザーがインストーラで追加。 ✅ 2026-07-08
- [x] **Diversion デスクトップクライアントが起動中**であること（プラグイン動作の前提）。 ✅ 2026-07-08
- [x] **5.8 対応 Diversion UE プラグイン**を FAB から入手可能か確認（現状 `.uproject` に marketplace 版 Diversion が有効）。 ✅ 2026-07-08
- [x] **VisualStudioTools プラグイン**：v2.8 は EngineVersion 未記載のため 5.8 でロード失敗の可能性。FAB/Marketplace の最新版入手 or 一時無効化（VS統合補助のためゲーム動作には非必須）を判断。 ✅ 2026-07-08

### Phase 1 — Diversion 移行ブランチ作成（ユーザー操作中心）
- [x] `E:\UEProjects\Colours` で作業ツリーがクリーンなことを確認（`cd E:\UEProjects\Colours; dv status`）。未コミット変更があればコミット。 ✅ 2026-07-08
- [x] **移行用ブランチを作成**（例 `upgrade/ue5-8`）。※ `dv` CLI のブランチ操作コマンドは未確認 → Diversion デスクトップクライアント or `dv` ヘルプで作成方法を確定してから実行。 ✅ 2026-07-08
- [x] このブランチに切替え、以降の作業を隔離。 ✅ 2026-07-08

### Phase 2 — エンジンバージョン切替
- [x] 再生成可能フォルダを削除：`Binaries/`, `Intermediate/`, `DerivedDataCache/`, `.vs/`（`Saved/` は設定退避後に削除可）。※ `.dvignore` で大半は無視対象だが `Binaries/` は追跡対象＝削除も差分になる。 ✅ 2026-07-08
- [x] **エンジン切替**：`Colours.uproject` を右クリック →「Switch Unreal Engine Version」→ 5.8、または `EngineAssociation` を `"5.3"` → `"5.8"` に直接編集。 ✅ 2026-07-08
- [x] **Visual Studio プロジェクトファイル再生成**（右クリック → Generate Visual Studio project files）。 ✅ 2026-07-08
- [/] **`Colours.uproject` の変更点**：
  - `EngineAssociation` → `"5.8"`
  - Diversion / VisualStudioTools プラグインの参照更新（Phase 0 の判断を反映）

### Phase 3 — C++ ビルド対応（Claude 実装 + ビルド反復）
- [x] **`Source\Colours.Target.cs` / `Source\ColoursEditor.Target.cs` を更新**： ✅ 2026-07-08
  - `IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_3` → **`Latest`**（5世代ジャンプかつ11ファイルと小規模のため段階昇格せず一括対応が効率的）
  - `DefaultBuildSettings = BuildSettingsVersion.V4` → 5.8 の最新（`V5` 等、5.8 で有効な最新値を確認して設定）
- [x] **VS でビルド**（Development Editor / Win64）。コンパイルエラーを反復修正。重点監視： ✅ 2026-07-08
  - **Geometry系**（`GeometryScriptingCore`, `GeometryCore`, `DynamicMesh`, `GeometryFramework`）の API 変更 → `ColoursDynamicConeComponent`, `DynamicErasableWall` 等が影響を受けやすい
  - **EnhancedInput** の非推奨/シグネチャ変更 → `ColoursCharacter`
  - include 順序変更による「未解決の型/未 include」エラー（IncludeOrderVersion 変更の主症状）
- [x] Phase 0 で記録した **UBT 不一致エラー**（`"Colours has build products in common with UnrealGame"`）が、エンジン＋UBT が 5.8 で揃うことで解消するか確認 → **本移行の主目的の一つ**。 ✅ 2026-07-08

### Phase 4 — エディタ起動・アセット/レベル移行
- [x] 5.8 エディタで `Colours.uproject` を起動。シェーダ再コンパイル完了を待つ。 ✅ 2026-07-08
- [x] **OFPA レベルの移行**：`__ExternalActors__` / `__ExternalObjects__` 配下が 5.8 形式へ更新される。主要マップを開いて保存： ✅ 2026-07-08
  - `Content\Colours\Levels\Test\ColourParameterTest.umap`
  - `Content\Colours\Levels\Test\LightParameterTest.umap`
- [x] **アセット再保存**：非推奨ノード/リダイレクタ警告を確認。必要なら「Resave All」で一括更新（差分は巨大化する点に留意）。 ✅ 2026-07-08
- [x] **`Config\DefaultEngine.ini` のレンダラ設定確認**：5.8 で Lumen/Nanite/Substrate 等の既定値が変わっていないか、意図せぬ見た目変化がないか検証。 ✅ 2026-07-08

### Phase 5 — 動作検証
- [x] 主要マップで PIE 実行し破綻がないこと。 ✅ 2026-07-08
- [ ] **カラーシステム**（CS-1〜3：`ColoursColorBase/InkValue/LightValue`、混色 operator、CS-3 照合判定関数）が想定通り動作。
- [x] **ギミック**：コーンライト（`ColoursConeLight` / `ColoursDynamicConeComponent`）、消える壁（`ErasableWall` / `DynamicErasableWall`）、`AutoMoverComponent`。 ✅ 2026-07-08
- [ ] エディタ Output Log にエラー/重大 Warning が残っていないこと。

### Phase 6 — Vault / プロジェクト文書の更新（Claude）
- [ ] [[070.020.現在地|現在地.md]]：技術スタック「Unreal Engine 5.3」→「5.8」。「次の実装タスク」の **UBT 不一致課題をクローズ**。
- [ ] [[Claudeと一緒にやること]]：`UE5.8への移行手順を考える` と `ビルド環境調査` を完了化（移行で解消）。
- [ ] プロジェクト側 `E:\UEProjects\Colours\ARCHITECTURE.md` / `README.md` のエンジンバージョン記述を更新。
- [ ] （任意）実装ログに移行記録を 1 本追加（`070.040.実装ログ/260706.UE5-8移行.md` 等）。

### Phase 7 — コミット・マージ・共有
- [x] **移行ブランチで dv コミット**：`cd E:\UEProjects\Colours; dv commit -a -m "UE5.3→5.8 移行"`。※ **Binaries/ + 再保存アセットで巨大コミット**になる想定。 ✅ 2026-07-08
- [ ] **Vault 側は git コミット**（文書更新分）。二重コミット規約は `/colours-task-end`・`/colours-day-end` に従う。
- [x] 検証完了後、**移行ブランチを main へマージ**。 ✅ 2026-07-08
- [x] **ヒルタへ共有**：マージ後に dv sync ＋ローカル再ビルドが必要（Binaries 追跡のため）。5.8 への切替タイミングを明示的に連絡。 ✅ 2026-07-08

---

## リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| Geometry系 API の破壊的変更 | ビルド不能 | Phase 3 で重点対応。UE5.8 リリースノート/非推奨一覧を該当クラスごとに参照 |
| VisualStudioTools が 5.8 で非対応 | エディタ起動失敗 | 最新版入手 or 無効化（ゲーム動作に非必須）|
| Diversion プラグインの版ずれ | VCS 統合不動 | FAB の 5.8 対応版へ更新。デスクトップクライアント起動を前提化 |
| 巨大 dv コミット（Binaries+Content 追跡）| 同期負荷・ヒルタ影響 | 移行ブランチで隔離。マージ時にヒルタへ再ビルド周知 |
| レンダラ既定値変化で見た目リグレッション | 品質劣化 | Phase 4 で DefaultEngine.ini とマップ実機確認 |
| dv ブランチ操作コマンド未確認 | 手順ブロック | Phase 1 冒頭でクライアント/CLI のブランチ方法を確定してから着手 |

---

## 検証方法（エンドツーエンド）

1. **ビルド**：VS で Development Editor / Win64 がエラー 0 で通過。UBT 不一致エラーが再発しない。
2. **エディタ起動**：5.8 で `Colours.uproject` が起動し、Output Log にエラーなし。
3. **プレイ**：`ColourParameterTest` / `LightParameterTest` で PIE 実行し、カラーシステム・ライト・消える壁ギミックが機能。
4. **VCS**：移行ブランチで `dv status` → `dv commit` が成功。main マージ後にヒルタ環境で sync＋ビルドが通ることを確認。

---

## 主要変更ファイル

- `E:\UEProjects\Colours\Colours.uproject`（EngineAssociation・プラグイン参照）
- `E:\UEProjects\Colours\Source\Colours.Target.cs` / `ColoursEditor.Target.cs`（IncludeOrderVersion・DefaultBuildSettings）
- `E:\UEProjects\Colours\Source\Colours\**`（非推奨 API 対応：Geometry系・EnhancedInput 依存クラス）
- `E:\UEProjects\Colours\Config\DefaultEngine.ini`（レンダラ既定値の確認・必要時調整）
- Vault：[[070.020.現在地|現在地.md]]・[[Claudeと一緒にやること]]（＋実装ログ任意）
- プロジェクト：`ARCHITECTURE.md`・`README.md`

## 担当分担

- **ユーザー操作**：UE5.8 インストール、VS ツールチェーン整備、Diversion クライアント起動、dv ブランチ作成/マージ、エンジン切替 GUI 操作、エディタ起動、ヒルタ連絡。
- **Claude 実装**：Target.cs 編集、C++ 非推奨 API 対応、Config 確認、Vault/プロジェクト文書更新、dv/git コミット文面。
