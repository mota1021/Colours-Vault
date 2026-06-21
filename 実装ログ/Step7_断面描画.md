# Step7 実装ログ: 断面描画

## 実装日
2026-06-14

## 対応バックログ
[[実装バックログ]] > Step7: 断面描画

---

## 課題

コーン消去でできた穴を覗くと、円錐の側面（斜めのトンネル内壁）にポリゴンが存在しないため、穴の奥がスカスカに見える。

**よくある誤解**: Two Sided / TwoSidedSign は「箱の反対側の面」を見せるだけで、円錐の斜め内壁は生成しない。→ Two Sided は解決策にならない。

---

## 方針: 断面プラグ（円錐メッシュ）方式

実際の円錐メッシュを光源の円錐に一致させて配置し、その**内壁**を描画して断面に見せる。

### 既存資産の再利用
- `AErasableWall` は Step3 で円錐パラメータ（LightPos/LightDir/CosConeAngle/Range/Active）を受信済み。
- 自分の境界ボックス（VisualMesh/DetectionBox extents）も保持している。
- → 断面プラグを **`AErasableWall` の子 `UStaticMeshComponent`** にすれば追加の同期配線が最小で済む。

---

## 実装手順

### 1. 断面プラグ用コンポーネント追加
Engine の Cone（または自作の内向き法線円錐メッシュ）を `AErasableWall` に
子 `UStaticMeshComponent`（名前例: `ConeSectionMesh`）として追加する。

### 2. Transform同期
円錐パラメータ受信時（Step3 の経路）にプラグを更新する。

| パラメータ | 設定値 |
|---|---|
| 位置 | LightPos（円錐の頂点 apex） |
| 向き | LightDir（軸）。`FRotationMatrix::MakeFromZ(LightDir)` 等で軸合わせ |
| 母線長（Z スケール） | Range |
| 底面半径（XY スケール） | `tan(半角) × Range`（半角 = acos(CosConeAngle)、または sin/cos で算出し acos 回避） |
| 可視性 | Active と連動 |

### 3. プラグ用マテリアル（新規作成）
**設定**: Masked ブレンド / Two Sided ON

#### Box clip（壁の外側フラグメントを破棄）
壁の AABB（中心 + ハーフエクステント）と比較し、壁の外側にあるフラグメントを clip。
→ 壁の厚み内を通る円錐バンドのみ描画される。

```
// 擬似コード（マテリアルグラフ内 Custom HLSL または ノード）
float3 localPos = TransformWorldToLocal(AbsoluteWorldPosition);
clip(HalfExtent - abs(localPos));  // 全軸で AABB 内に収める
```

#### 内壁法線補正
Two Sided で背面（内壁）が描画されるが、そのままでは法線が外向きで暗くなる。
`TwoSidedSign`（表面=+1 / 裏面=−1）を `Constant3Vector(0,0,1)` と乗算し Normal に接続。
→ 裏面で法線が反転し、光を正しく受ける（タンジェント空間のまま使用可・Tangent Space Normal 設定変更不要）。

#### BaseColor
壁マテリアルと同じ色を使用し、断面が壁と同色に見えるようにする。

### 4. 整合確認
消去シェーダー（Step4）と**同一の円錐パラメータ**を使うため、プラグ側面と穴の縁が一致するはず。
ズレる場合はパラメータ受け渡しの単位・座標系を点検する。

---

## 注意点・既知リスク

- **Z-fighting**: 穴の縁でプラグ外面と壁面が重なる可能性がある。必要なら微小深度オフセット。
- **複数光源**: 1つの壁を複数の光源が照らす構成は本 Step のスコープ外。プロト段階は「1壁=1サーチライト」を前提とする。

---

## 完了条件

- 円錐穴を覗くと、斜めのトンネル内壁が壁色で描画されることをUEで確認 ← **エディタ側マテリアル作成後に確認要**
- 穴の縁とプラグ側面がズレていないことを確認（Z-fighting が許容範囲内であること）

---

## ✅ Claude 実装済み（コード/ドキュメント）
- [x] `AErasableWall` コンポーネント構成リファクタ（`ErasableWall.h/.cpp`、2026-06-19）
  - 状況: `USceneComponent* SceneRoot` を追加して新 RootComponent に。全子コンポーネントを SceneRoot にアタッチ。`RebuildSegments` で VisualMesh をネイティブ bbox から自動スケール・自動配置。`docs/Architecture/Gimmick.md` にサイズ運用ルールを追記。
- [x] コーン向き反転を修正（`ErasableWall.cpp:UpdateConeSection`）
- [x] `docs/Architecture/Gimmick.md` の transform 公式を修正
- [x] `CLAUDE.md` に実装ログのチェックリスト規約を追記
- [x] BeginPlay で MID 生成・クリップ params を設定（OnConstruction MID の PIE 消失対策）
- [x] `ConeSectionMaterial` UPROPERTY 割当必須を `docs/Architecture/Gimmick.md` に注記
- [x] 移動壁対応：`Tick` + `RefreshConeSection()` でクリップ params とコーン Transform を 60fps で再適用（`ErasableWall.h/.cpp`、2026-06-14）
  - 状況: `AutoMoverComponent` が壁を毎フレーム移動させる場合、`WallCenterWS` 等が陳腐化して断面が透明になる問題を修正。`UpdateConeSection` で光源パラメータをキャッシュし、Tick が `RefreshConeSection` を呼んで追従する。Tick は非アクティブ時 `SetActorTickEnabled(false)` で停止する。
- [x] `ConeSectionMesh->SetAbsolute(true, true, true)` でコーン震え修正（`ErasableWall.cpp` コンストラクタ、2026-06-14）
  - 状況: `AutoMoverComponent` の `SetActorLocation` がアタッチ子を引きずりコーンが震えていた。ワールド座標固定で解消。`docs/Architecture/Gimmick.md` に再発防止注記追加。

## ⬜ ユーザー作業（UEエディタ）
- [x] `Content/` にマテリアル `M_ConeSection` を新規作成（詳細は下記「マテリアル構築ガイド」参照） ✅ 2026-06-14
  - 状況:
    - ~~コーンが全く描画されない~~ → パラメータ名修正で解消。
    - ~~内壁が真っ黒~~ → Normal 入力を未接続にすることで解消（`TwoSidedSign × (0,0,1)` は UE の Two Sided 自動反転と二重反転になり逆効果だった）。
- [x] `AErasableWall` Detail の `ConeSectionMaterial` に `M_ConeSection` を割当 ✅ 2026-06-14
  - 状況:

## ⬜ 動作検証（ユーザー・PIE）
- [x] コーン本体がライトの向き（forward）に開く ✅ 2026-06-14
  - 状況:
- [x] 穴を覗いて内壁が壁色で描画される ✅ 2026-06-19
  - 状況:
    - ~~極一部の領域のみが真っ黒で描画される。この領域はBOXの移動に伴って出現したり消滅したりする。~~
    - **原因確定（2026-06-19）**: 配置した壁アクターに Transform スケールをかけていたことが原因。`ApplyConeSectionClipParams` はアクタースケール非対応（`WallHalfExtent` は生値・`WallCenterWS` は Transform 込み → desync してクリップ箱が壁より小さくなり断面が削れて黒く欠けた）。ライティング/影は原因ではなかった。
    - **対処（2026-06-19）**: コンポーネント構成をリファクタ。`USceneComponent* SceneRoot` を新 RootComponent にし、全子コンポーネントをアタッチ。`WallHalfExtent` を唯一のサイズ正本とし、`RebuildSegments` が VisualMesh スケール・DetectionBox・Segments・クリップ箱を一括再構築するよう変更。アクター Transform スケールは (1,1,1) 固定、サイズ変更は `WallHalfExtent` のみで行う運用に統一。
- [ ] 穴の縁とプラグ側面がズレていない（Z-fighting 許容範囲内）
  - 状況:

---

## 実装結果（2026-06-14）

### 仕様との差異
仕様メモは「AErasableWall が自身でコーンパラメータを保持して更新」前提だったが、実コードでは
**AErasableWall は受動的**。コーンパラメータは `AColoursConeLight` がライブ算出して push する設計のため、
それに合わせて `UpdateConeSection()` を public API として追加し、既存の push 経路（`UpdateErasableWallSegments`）から呼ぶ形にした。

### 追加した C++ 変更
- `ErasableWall.h/.cpp`: `ConeSectionMesh`（UStaticMeshComponent）と `UpdateConeSection()` を追加。
  `RebuildSegments` で Box clip 用の壁 AABB パラメータを MID に静的セット。
- `ColoursConeLight.cpp`: `UpdateErasableWallSegments`（壁ごと `true`）・release ループ・`EndPlay`（`false`）で呼び出し配線。
- `ARCHITECTURE.md`: Gimmick クラス構造をプロジェクトルートに文書化。

### マテリアル構築ガイド（M_ConeSection 詳細手順）

---

#### ⚠️ 最重要：「パラメータ」と「ノード」の区別

| 種類 | 意味 | 本マテリアルでの数 |
|---|---|---|
| **VectorParameter（パラメータ）** | C++ が実行時に値を書き込む「名前付きの箱」。名前を C++ コードと **1文字も違わず**一致させることが必須。ユーザーが値を手入力する必要はない | 5個（下表） |
| **ノード** | シェーダー内でデータを取得・計算する関数。`AbsoluteWorldPosition` など。ユーザーが値を入れるものではない | 残り全部 |

C++（`ErasableWall.cpp`）が実行時に自動でセットする VectorParameter 一覧：

| パラメータ名（完全一致必須） | C++ が入れる値 | 用途 |
|---|---|---|
| `WallCenterWS` | 壁 AABB の中心ワールド座標 = `ActorLocation + (0, 0, WallHalfExtent.Z)` | Box clip の原点 |
| `WallHalfExtent` | 壁の半サイズ (X=厚み, Y=幅, Z=高さ) | Box clip の範囲 |
| `WallAxisX` | 壁の Right 方向（ワールド空間単位ベクトル） | 厚み軸 |
| `WallAxisY` | 壁の Forward 方向（ワールド空間単位ベクトル） | 幅軸 |
| `WallAxisZ` | 壁の Up 方向（ワールド空間単位ベクトル） | 高さ軸 |

> **なぜ ActorLocation そのままではないか**: `AErasableWall` の原点規約は**底面中心**（`SceneRoot` が底面中心 = ワールド原点）。
> 箱の幾何中心は底面から `WallHalfExtent.Z` だけ上にある。C++ では
> `GetActorTransform().TransformPosition(FVector(0, 0, WallHalfExtent.Z))` でこのオフセットを適用している（`ErasableWall.cpp:202`）。

> **名前が1文字でも違うと `SetVectorParameterValue` は黙って何もしない。**
> `WallHalfExtent` が既定値 `(0,0,0)` のまま → Box clip が全ピクセルを破棄 → コーンが全く描画されない。
> これが「コーンが全く描画されない」の最有力原因。

---

#### 0. マテリアル基本設定

Detail パネル上部で設定：

- **Blend Mode**: Masked
- **Two Sided**: ON（チェックを入れる）
- **Shading Model**: Default Lit

---

#### A. 作成する VectorParameter（5個）

マテリアルグラフの空白を右クリック → `VectorParameter` で作成。各パラメータの **Parameter Name** を下表のとおり正確に設定する。

| Parameter Name | Default Value（プレビュー用目安） |
|---|---|
| `WallCenterWS` | (0, 0, 150, 0) |
| `WallHalfExtent` | (25, 100, 150, 0) |
| `WallAxisX` | (1, 0, 0, 0) |
| `WallAxisY` | (0, 1, 0, 0) |
| `WallAxisZ` | (0, 0, 1, 0) |

---

#### B. データ取得ノード（値を入れない・右クリック検索で追加するだけ）

- `AbsoluteWorldPosition`：現在描画中のピクセルのワールド座標（シェーダーが自動供給）

---

#### C. OpacityMask = Box clip（Custom ノード）

1. 右クリック → `Custom` でノード追加。
2. Detail の **Code** 欄に以下を貼り付け：

```hlsl
float3 d = WorldPos - Center;
float3 local = float3(dot(d, Ax), dot(d, Ay), dot(d, Az));
float3 m = Half - abs(local);
return (m.x > 0 && m.y > 0 && m.z > 0) ? 1.0 : 0.0;
```

3. Detail の **Inputs** に6つの入力ピンを追加：

| Input Name | 接続元                              |
| ---------- | -------------------------------- |
| `WorldPos` | `AbsoluteWorldPosition`          |
| `Center`   | VectorParameter `WallCenterWS`   |
| `Half`     | VectorParameter `WallHalfExtent` |
| `Ax`       | VectorParameter `WallAxisX`      |
| `Ay`       | VectorParameter `WallAxisY`      |
| `Az`       | VectorParameter `WallAxisZ`      |

4. Custom ノードの出力ピン → **OpacityMask** に接続。

---

#### D. Normal = **未接続（デフォルトのまま）**

> ⚠️ **`TwoSidedSign × (0,0,1) → Normal` は接続してはいけない（確認済み）。**
> UE の Two Sided マテリアルは裏面の法線を自動反転する。`TwoSidedSign` でさらに反転すると
> **二重反転**になり、内壁の法線が光源と逆を向いて真っ黒になる（症状⑤で確認）。
>
> **Normal 入力は何も繋がない（デフォルト）が正解。** UE の自動処理に委ねる。

---

#### E. BaseColor

- 右クリック → `Constant3Vector` を追加し、壁と同じ色に設定（例：灰色なら `(0.5, 0.5, 0.5)`）
- → **BaseColor** に接続。
- 後で壁色に合わせたい場合は `VectorParameter` にして色を変えられるようにしてもよい。

---

#### F. BP への割当

`AErasableWall` の Detail パネル「ConeSection」カテゴリ → `ConeSectionMaterial` に `M_ConeSection` を割当。
C++ の `EnsureConeSectionMID()` が `BeginPlay` 時に MID を自動生成してパラメータを書き込む。ユーザーが値を手入力する必要はない。

---

#### G. デバッグ手順

##### 症状A — 全く描画されない（コーンが見えない）

**Step A-1** OpacityMask を一時的に `Constant 1` に差し替えてコーンが見えるか確認。
- 見える → clip 側の問題（症状B へ）。
- 見えない → `ConeSectionMaterial` 割当・ライト稼働中（PIEで光源が動作しているか）を確認。

**Step A-2** VectorParameter 名を A 節の表と1文字ずつ比較。`WallHalfExtent` が `(0,0,0)` のまま → 全ピクセル破棄。

---

##### 症状B — コーン全体が常に描画される（壁の外側まで見える）

`WallAxisX/Y/Z` のいずれかが零ベクトル `(0,0,0)` になっている。
内積が常に 0 → Margin が常に正 → 全ピクセルが「内側」判定になる。

**Step B-1** 各 VectorParameter を **1つずつ EmissiveColor に差し替えて PIE で色を読む。**

| EmissiveColor に繋ぐもの | 期待色（壁が回転していない場合） | 黒だったら |
|---|---|---|
| `WallAxisX`（= Actor Right ≈ +Y world） | 緑 (0, 1, 0) 系 | 零ベクトル → 原因確定 → Step B-2 へ |
| `WallAxisY`（= Actor Forward ≈ +X world） | 赤 (1, 0, 0) 系 | 零ベクトル → 原因確定 → Step B-2 へ |
| `WallAxisZ`（= Actor Up = +Z world） | 青 (0, 0, 1) 系 | 零ベクトル → 原因確定 → Step B-2 へ |
| `WallHalfExtent` を `Divide(÷200)` した値 | 薄い灰色（正の色） | C++ から設定されていない |
| `WallCenterWS` を `Divide(÷1000)` した値 | 何らかの色 | C++ から設定されていない |

**Step B-2** 軸が黒の場合：そのノードが `VectorParameter` でなく `Constant3Vector`（定数）になっている。
ノードを右クリック → **Convert to Parameter** → Parameter Name を `WallAxisX`（等）に設定 → Save。

**Step B-3** 軸が正しい色なのに常時描画される場合：Custom ノードの HLSL でピン名と変数名が一致しているか確認（`Ax`/`Ay`/`Az` のスペルミス等）。

---

##### 症状C — 内壁が真っ黒

**Normal に `TwoSidedSign × (0,0,1)` を繋いでいる**。これは二重反転になり逆効果。
Normal 入力への接続をすべて外す（未接続にする）。

---

**フォールバック（パラメータが黒のまま直らない＝C++ が MID に値を入れていない疑い）**

`ErasableWall.cpp` の `ApplyConeSectionClipParams()` 内に一時 `UE_LOG` を追加し、
`ConeSectionMID` の有効性と各 Axis 値を PIE ログで確認する（要ビルド・最終手段）。

---

2. `AErasableWall` の Detail パネル「ConeSection」カテゴリ → `ConeSectionMaterial` に `M_ConeSection` を割当（割当済み ✅ 2026-06-14）。

### 発生バグと修正（2026-06-14、続き）

**症状④**: 移動壁（AutoMoverComponent）でコーンメッシュがぶるぶる震える。

**原因**: `ConeSectionMesh` は `RootComponent` にアタッチされており、`AutoMoverComponent::TickComponent` の `SetActorLocation` が壁アクターを動かすたびにコーンメッシュも引きずられる。`RefreshConeSection` が次 Tick で正しいワールド座標に戻すが、この往復が毎フレーム発生して震えになる。

**修正**: コンストラクタで `ConeSectionMesh->SetAbsolute(true, true, true)` を追加。ワールド座標固定にすることで親アクターの移動に引きずられなくなり、`SetWorldTransform` だけが位置を制御する。

**症状⑤**: M_ConeSection 内壁が真っ黒（ライティングが届かない）。

**原因**: `TwoSidedSign × Constant3Vector(0,0,1) → Normal` の接続が逆効果だった。UE の Two Sided マテリアルは裏面の法線を自動反転するため、さらに `TwoSidedSign` で反転すると二重反転になり、内壁の法線が光源と逆を向いて黒くなる。

**修正**: M_ConeSection の Normal 入力を未接続にする（UE の自動処理に委ねる）。

---

### 発生バグと修正（2026-06-14）

**症状①**: コーン本体がライトの向き（forward）と逆向きに開く。頂点（apex）はライト原点に乗るが、本体が背後に展開する。

**原因**: Engine Cone の apex は local +Z。`MakeFromZ(LightDir)` で +Z を +LightDir に向けると apex は前を向くが、
本体（−Z 側）が −LightDir（背後）に開いてしまう。

**修正**: `ErasableWall.cpp:UpdateConeSection` の回転と中心位置を反転。
- 変更前: `MakeFromZ(LightDir)` / `WorldLoc = LightPos − LightDir*(Range*0.5)`
- 変更後: `MakeFromZ(-LightDir)` / `WorldLoc = LightPos + LightDir*(Range*0.5)`

**症状②**: `ConeSectionMaterial` プロパティ（UPROPERTY）を BP/インスタンスで割り当てていなかったため、`EnsureConeSectionMID()` が MID を生成せず、クリップ params が一度もセットされなかった（全軸が黒）。

**修正**: BP の Details「ConeSection」→ `ConeSectionMaterial` に `M_ConeSection` を割当（2026-06-14 ユーザー実施）。

**症状③**: `AutoMoverComponent` が壁を毎フレーム移動させる場合、`WallCenterWS`/`WallAxisX/Y/Z` が `BeginPlay` 時の位置に凍結され、コーン断面が透明になる。

**原因**: クリップ params はアクター Transform に依存するが、`BeginPlay` 後に壁が移動してもパラメータを再セットする経路が無かった。

**修正**: `Tick`（60fps）で `RefreshConeSection()` を呼び、クリップ params とコーン mesh Transform を毎フレーム再計算・再適用する。光源パラメータ（LightPos/Dir/CosConeAngle/Range）はキャッシュして使用。Tick は非アクティブ時 `SetActorTickEnabled(false)` で停止（2026-06-14）。

---

## 次の Step への申し送り

- Step8（負荷調整）へ → [[Step8_負荷調整]]
