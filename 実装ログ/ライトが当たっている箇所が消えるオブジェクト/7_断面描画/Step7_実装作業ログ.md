%%
【記述原則】
- コード作業の詳細は書かない（git/コードで確認可）
- 非コード作業（BP配線・パラメータ設定・データテーブル作成・マテリアルノード等）は
  バイナリでdiffが効かないため、後から再現できる手順を書く
  （依頼した作業指示をそのままコピペする程度の具体度）
- 日付は書かない（コミット履歴で確認可）
- 各エントリの対応TaskはTask MasterのタスクID参照1行のみ
%%

→ [[Step7_実装計画]]

完了状況: 進行中

---

## Step7: 断面描画

### 実施内容

コード作業:
- `AErasableWall` を `SceneRoot`（`USceneComponent`）化リファクタ。全子コンポーネントを SceneRoot にアタッチし、`WallHalfExtent` をサイズの唯一の正本とした。`RebuildSegments` が VisualMesh スケール・DetectionBox・Segments・クリップ箱を一括再構築するよう変更。アクター Transform スケールは (1,1,1) 固定運用に統一。
- コーン向き反転の修正（`MakeFromZ` の引数と配置 Offset を反転）。
- BeginPlay で MID 生成・クリップ params を設定（OnConstruction MID の PIE 消失対策）。
- 移動壁対応: `Tick`（60fps）で `RefreshConeSection()` を呼び、クリップ params とコーン Transform を毎フレーム再計算・再適用。非アクティブ時は `SetActorTickEnabled(false)` で停止。
- `ConeSectionMesh`（`UStaticMeshComponent`）→ `ConeSectionPlug`（`UDynamicMeshComponent`）へ型変更。詳細は「設計変更」参照。

非コード作業（UEエディタ）:
- `Content/` にマテリアル `M_ConeSection` を新規作成。**Normal 入力は未接続にすること**（接続すると二重反転になり内壁が真っ黒になる）。
- `AErasableWall` Detail パネルの「ConeSection」カテゴリ → `ConeSectionMaterial` に `M_ConeSection` を割当。
- 壁アクターの Transform スケールは `(1,1,1)` 固定。サイズ変更は `WallHalfExtent` のみで行う。

### 発生した問題

- **問題**: コーン本体が逆向きに開く（ライト背後方向）。
- **原因**: Engine Cone の apex は local +Z。`MakeFromZ(LightDir)` では apex が前を向き、本体（−Z 側）が背後に開く。
- **解決方法**: `MakeFromZ(-LightDir)` に変更し、Offset を `LightPos + LightDir*(Range*0.5)` に修正。

---

- **問題**: `ConeSectionMaterial` 未割当により MID が生成されず、クリップ params が全軸黒のまま。
- **原因**: BP/インスタンスで `ConeSectionMaterial` UPROPERTY を割り当てていなかった。
- **解決方法**: BP の Details「ConeSection」→ `ConeSectionMaterial` に `M_ConeSection` を割当（ユーザー実施）。

---

- **問題**: 移動壁でコーン断面が透明になる。
- **原因**: クリップ params が `BeginPlay` 時の Transform で固定されており、壁移動後に再セットする経路がなかった。
- **解決方法**: `Tick`（60fps）で `RefreshConeSection()` を毎フレーム呼ぶ。光源パラメータはキャッシュして使用。

---

- **問題**: 移動壁でコーンメッシュが震える。
- **原因**: `ConeSectionMesh` が RootComponent にアタッチされており、`AutoMoverComponent` の `SetActorLocation` でコーンが引きずられ、`RefreshConeSection` が次 Tick で正しい座標に戻す往復が毎フレーム発生。
- **解決方法**: コンストラクタで `ConeSectionPlug->SetAbsolute(true, true, true)` を追加し、ワールド座標固定にする。

---

- **問題**: 内壁が真っ黒（ライティングが届かない）。
- **原因**: `TwoSidedSign × Constant3Vector(0,0,1) → Normal` が逆効果。UE の Two Sided マテリアルは裏面法線を自動反転するため、`TwoSidedSign` でさらに反転すると二重反転になり内壁の法線が光源と逆を向く。
- **解決方法**: `M_ConeSection` の Normal 入力を未接続にする（UE の自動処理に委ねる）。

---

- **問題**: 断面の一部が黒く欠ける・壁移動に伴って欠け領域が出現・消滅する。
- **原因**: 配置した壁アクターに Transform スケールをかけていたことが原因。`ApplyConeSectionClipParams` はアクタースケール非対応（`WallHalfExtent` は生値・`WallCenterWS` は Transform 込み → desync してクリップ箱が壁より小さくなり断面が削れた）。
- **調査内容**: ライティング・影は原因ではなかった。
- **解決方法**: `SceneRoot` 化リファクタで `WallHalfExtent` をサイズ唯一の正本とし、アクター Transform スケールを (1,1,1) 固定運用に統一。

### 設計変更

- **変更前**: `ConeSectionMesh`（`UStaticMeshComponent` / Engine Cone・分割数固定）
- **変更後**: `ConeSectionPlug`（`UDynamicMeshComponent` / GeometryScript で `ConeSectionRadialSteps` 分割のコーンを実行時生成）
- **理由**: Engine Cone は分割数が固定で縁がカクつくため、高精細コーンに変更。

### 残課題・TODO

- 穴の縁とプラグ側面のズレ（Z-fighting 許容範囲内か）の PIE 検証が未完。

### 動作確認結果

- コーン本体がライトの向き（forward）に開くことを確認。
- 穴を覗いて内壁が壁色で描画されることを確認。
- Z-fighting（穴の縁とプラグ側面のズレ）は未検証。

### 知見

- UE で型変更（`UStaticMeshComponent` → `UDynamicMeshComponent`）する際は、`FName`（サブオブジェクト名）とメンバー変数名の **両方** をリネームしないと、BP 派生クラスをリコンパイルしても旧名のサブオブジェクトが .uasset に残りプロパティが null になる。
- UE の Two Sided マテリアルは裏面の法線を自動反転する。Normal ノードを TwoSidedSign でさらに反転させると二重反転になるため、Normal 入力は未接続が正解。
- ヒット判定の重処理（`PerformConeTrace` 20Hz）と視覚更新（`Tick` 60fps）は頻度を分離するとよい。
