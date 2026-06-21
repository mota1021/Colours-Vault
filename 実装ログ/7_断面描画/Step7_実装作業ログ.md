# Step7: 断面描画 — 実装作業ログ

## 関連
- [[Step7_断面描画]] — 課題・方針・完了条件
- [[Step7_実装計画]] — 実装手順・マテリアル構築ガイド

---

## 作業チェックリスト

### ✅ Claude 実装済み（コード/ドキュメント）
- [x] `AErasableWall` コンポーネント構成リファクタ（`ErasableWall.h/.cpp`、2026-06-19）
  - `USceneComponent* SceneRoot` を追加して新 RootComponent に。全子コンポーネントを SceneRoot にアタッチ。`RebuildSegments` で VisualMesh をネイティブ bbox から自動スケール・自動配置。`docs/Architecture/Gimmick.md` にサイズ運用ルールを追記。
- [x] コーン向き反転を修正（`ErasableWall.cpp:UpdateConeSection`）
- [x] `docs/Architecture/Gimmick.md` の transform 公式を修正
- [x] `CLAUDE.md` に実装ログのチェックリスト規約を追記
- [x] BeginPlay で MID 生成・クリップ params を設定（OnConstruction MID の PIE 消失対策）
- [x] `ConeSectionMaterial` UPROPERTY 割当必須を `docs/Architecture/Gimmick.md` に注記
- [x] 移動壁対応：`Tick` + `RefreshConeSection()` でクリップ params とコーン Transform を 60fps で再適用（`ErasableWall.h/.cpp`、2026-06-14）
- [x] `ConeSectionPlug->SetAbsolute(true, true, true)` でコーン震え修正（`ErasableWall.cpp` コンストラクタ、2026-06-14）
- [x] `ConeSectionMesh`（UStaticMeshComponent）→ `ConeSectionPlug`（UDynamicMeshComponent）へ型変更（2026-06-20）

### ⬜ ユーザー作業（UEエディタ）
- [x] `Content/` にマテリアル `M_ConeSection` を新規作成 ✅ 2026-06-14
  - ~~コーンが全く描画されない~~ → パラメータ名修正で解消。
  - ~~内壁が真っ黒~~ → Normal 入力を未接続にすることで解消。
- [x] `AErasableWall` Detail の `ConeSectionMaterial` に `M_ConeSection` を割当 ✅ 2026-06-14

### ⬜ 動作検証（ユーザー・PIE）
- [x] コーン本体がライトの向き（forward）に開く ✅ 2026-06-14
- [x] 穴を覗いて内壁が壁色で描画される ✅ 2026-06-19
  - ~~極一部の領域のみが真っ黒で描画される。この領域はBOXの移動に伴って出現したり消滅したりする。~~ → 症状⑥参照。
- [ ] 穴の縁とプラグ側面がズレていない（Z-fighting 許容範囲内）

---

## 不具合対応ログ

### 症状① コーンが逆向きに開く（2026-06-14）

**原因**: Engine Cone の apex は local +Z。`MakeFromZ(LightDir)` で +Z を +LightDir に向けると apex は前を向くが、本体（−Z 側）が背後（−LightDir）に開く。

**修正** (`ErasableWall.cpp:UpdateConeSection`):
- 変更前: `MakeFromZ(LightDir)` / `WorldLoc = LightPos − LightDir*(Range*0.5)`
- 変更後: `MakeFromZ(-LightDir)` / `WorldLoc = LightPos + LightDir*(Range*0.5)`

---

### 症状② ConeSectionMaterial 未割当により MID が生成されない（2026-06-14）

**原因**: BP/インスタンスで `ConeSectionMaterial` UPROPERTY を割り当てていなかったため `EnsureConeSectionMID()` が MID を生成せず、クリップ params が未セット（全軸が黒）。

**修正**: BP の Details「ConeSection」→ `ConeSectionMaterial` に `M_ConeSection` を割当（ユーザー実施）。

---

### 症状③ 移動壁でコーン断面が透明になる（2026-06-14）

**原因**: クリップ params は `BeginPlay` 時の Transform で固定されており、壁移動後に再セットする経路がなかった。

**修正**: `Tick`（60fps）で `RefreshConeSection()` を呼び、クリップ params とコーン Transform を毎フレーム再計算・再適用。光源パラメータ（LightPos/Dir/CosConeAngle/Range）はキャッシュして使用。Tick は非アクティブ時 `SetActorTickEnabled(false)` で停止。

---

### 症状④ 移動壁でコーンメッシュが震える（2026-06-14）

**原因**: `ConeSectionMesh` が `RootComponent` にアタッチされており、`AutoMoverComponent::TickComponent` の `SetActorLocation` がコーンも引きずる。`RefreshConeSection` が次 Tick で正しい座標に戻す往復が毎フレーム発生して震え。

**修正**: コンストラクタで `ConeSectionPlug->SetAbsolute(true, true, true)` を追加。ワールド座標固定にすることで親 Actor の移動に引きずられなくなる。

---

### 症状⑤ 内壁が真っ黒（ライティングが届かない）（2026-06-14）

**原因**: `TwoSidedSign × Constant3Vector(0,0,1) → Normal` が逆効果。UE の Two Sided マテリアルは裏面の法線を自動反転するため、さらに `TwoSidedSign` で反転すると二重反転になり内壁の法線が光源と逆を向く。

**修正**: `M_ConeSection` の Normal 入力を未接続にする（UE の自動処理に委ねる）。

---

### 症状⑥ 断面の一部が黒く欠ける・移動で出現消滅する（2026-06-19）

**原因**: 配置した壁アクターに Transform スケールをかけていたことが原因。`ApplyConeSectionClipParams` はアクタースケール非対応（`WallHalfExtent` は生値・`WallCenterWS` は Transform 込み → desync してクリップ箱が壁より小さくなり断面が削れて欠けた）。ライティング/影は原因ではなかった。

**修正**: `USceneComponent* SceneRoot` を新 RootComponent にし、全子コンポーネントをアタッチ。`WallHalfExtent` を唯一のサイズ正本とし、`RebuildSegments` が VisualMesh スケール・DetectionBox・Segments・クリップ箱を一括再構築するよう変更。アクター Transform スケールは (1,1,1) 固定、サイズ変更は `WallHalfExtent` のみで行う運用に統一。

---

## ConeSectionPlug リファクタリング（2026-06-20）

**変更内容**: `ConeSectionMesh`（`UStaticMeshComponent`）→ `ConeSectionPlug`（`UDynamicMeshComponent`）へ型変更。

**理由**: Engine Cone（/Engine/BasicShapes/Cone）は分割数が固定で縁がカクつく。GeometryScript で `ConeSectionRadialSteps` 分割の高精細コーンを実行時生成することで解消。

**BP null クラッシュの罠**: 型変更後に BP 派生クラスをリコンパイルしても旧サブオブジェクト名 `ConeSectionMesh` が .uasset 内に残りプロパティが null になった。`FName`（`TEXT("ConeSectionMesh")` → `TEXT("ConeSectionPlug")`）とメンバー変数名を両方リネームすることで解消（→ [[DebuggingPlaybook]] 参照）。

**ColoursConeLight 変更**: `PerformConeTrace`（20Hz）から `ApplyMIDParams` + `UpdateConeSection` の呼び出しを削除し `Tick`（60fps）に移管。ヒット判定の重処理と視覚更新の頻度を分離。
