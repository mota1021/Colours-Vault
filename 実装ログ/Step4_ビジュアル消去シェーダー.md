# Step4 実装ログ: ビジュアル消去シェーダー

## 実装日
2026-06-13

## 対応バックログ
[[実装バックログ]] > Step4

---

## 実装方針

壁マテリアル（`M_Basic_Wall_Vanish`）を **Masked ブレンド**に設定。
C++（`ColoursConeLight.cpp`）が実行時に MID 経由でパラメータを書き込み、コーン内のピクセルを透明にする。

### シェーダーの計算式

```
D       = normalize(AbsoluteWorldPosition - LightPos)   // 光源 → ピクセルの方向
cone    = dot(D, LightDir)                               // 光軸との一致度（cos値）
inCone  = (cone > CosConeAngle) AND (dist < Range)       // コーン内判定
OpacityMask = inCone * Active                            // Active=0のとき全不透明
```

### 最適化ポイント
`cos(半角)` は CPU 側で 1 回だけ計算して `CosConeAngle` として渡す。ピクセルシェーダー内で `acos` を計算しない。

---

## 完了条件（達成済み）
BP からパラメータを渡すと壁の当該部分が透明になる動作を UE で確認できる。

---

## マテリアル構築ガイド（M_Basic_Wall_Vanish 詳細手順）

---

### ⚠️ 最重要：「パラメータ」と「ノード」の区別

| 種類 | 意味 | 本マテリアルでの数 |
|---|---|---|
| **VectorParameter / ScalarParameter（パラメータ）** | C++ が実行時に値を書き込む「名前付きの箱」。名前を C++ コードと **1文字も違わず**一致させることが必須。ユーザーが値を手入力する必要はない | 5個（下表） |
| **ノード** | シェーダー内でデータを取得・計算する関数。`AbsoluteWorldPosition` など。ユーザーが値を入れるものではない | 残り全部 |

C++（`ColoursConeLight.cpp`）が実行時に自動でセットするパラメータ一覧：

| パラメータ名（完全一致必須） | 型 | C++ が入れる値 | 用途 |
|---|---|---|---|
| `LightPos` | **VectorParameter** | 光源のワールド座標 | コーン頂点（apex）|
| `LightDir` | **VectorParameter** | 照射方向（単位ベクトル） | コーン軸 |
| `CosConeAngle` | **ScalarParameter** | cos(半角_rad) | コーン開き角の境界 |
| `Range` | **ScalarParameter** | cm（距離上限） | コーン長さ |
| `Active` | **ScalarParameter** | 1.0=消去中 / 0.0=非アクティブ | 消去の ON/OFF |

> **名前が1文字でも違うと `SetVectorParameterValue` / `SetScalarParameterValue` は黙って何もしない。**
> `Active` が常に 0 のまま → 壁が一切透明にならない。これが最多の原因。

---

### 0. マテリアル基本設定

Detail パネル上部で設定：

- **Blend Mode**: Masked
- **Two Sided**: OFF（壁は片面で十分）
- **Shading Model**: Default Lit

---

### A. 作成するパラメータ（5個）

マテリアルグラフの空白を右クリック → `VectorParameter` または `ScalarParameter` で作成。
**Parameter Name** を下表のとおり正確に設定する。

#### VectorParameter（2個）

| Parameter Name | Default Value（プレビュー用目安） |
|---|---|
| `LightPos` | (0, 0, 300, 0) |
| `LightDir` | (1, 0, 0, 0) |

#### ScalarParameter（3個）

| Parameter Name | Default Value（プレビュー用目安） |
|---|---|
| `CosConeAngle` | 0.866 （≈ 30° の cos） |
| `Range` | 1000 |
| `Active` | 0.0 |

---

### B. データ取得ノード（値を入れない・右クリック検索で追加するだけ）

- `AbsoluteWorldPosition`：現在描画中のピクセルのワールド座標

---

### C. OpacityMask の計算

#### C-1. Custom ノード版（推奨・先にこちらで動確）

1. 右クリック → `Custom` でノード追加。
2. Detail の **Code** 欄に以下を貼り付け：

```hlsl
float3 toPixel = normalize(WorldPos - LPos);
float cosAngle = dot(toPixel, LDir);
float dist     = length(WorldPos - LPos);
float inCone   = (cosAngle > CosAngle && dist < Rng) ? 1.0 : 0.0;
return 1 - inCone * Act;
```

3. Detail の **Inputs** に5つの入力ピンを追加：

| Input Name | 接続元 |
|---|---|
| `WorldPos` | `AbsoluteWorldPosition` |
| `LPos` | VectorParameter `LightPos` |
| `LDir` | VectorParameter `LightDir` |
| `CosAngle` | ScalarParameter `CosConeAngle` |
| `Rng` | ScalarParameter `Range` |
| `Act` | ScalarParameter `Active` |

4. Custom ノードの出力ピン → **OpacityMask** に接続。

---

#### C-2. 純ノードグラフ版（理解用・C-1 と同じ計算）

| ステップ | ノード | 何をしているか |
|---|---|---|
| ① | `AbsoluteWorldPosition` **−** `LightPos` | 光源 → ピクセルのベクトル **D** |
| ② | `Normalize(D)` | **D** を単位ベクトル化 |
| ③ | `Dot(Normalize(D), LightDir)` | 光軸との一致度（cos値）= `cosAngle` |
| ④ | `If(cosAngle > CosConeAngle → 1 / else → 0)` | 角度がコーン内か |
| ⑤ | `Length(D)` | 光源からの距離 = `dist` |
| ⑥ | `If(dist < Range → 1 / else → 0)` | 距離がRange内か |
| ⑦ | `Multiply(④, ⑥)` | 角度 AND 距離（両方 1 のときだけ 1） |
| ⑧ | `Multiply(⑦, Active)` | Active=0 のとき全不透明 |
| ⑨ | ⑧の出力 → **OpacityMask** | 完了 |

> `If` ノードは A≥B=True Side / A<B=False Side。  
> ④: A=`cosAngle`, B=`CosConeAngle`, TrueSide=1, FalseSide=0  
> ⑥: A=`Range`, B=`dist`, TrueSide=1, FalseSide=0（引数の順に注意）

---

### D. BaseColor

- 右クリック → `Constant3Vector` を追加し、壁の色を設定（例：灰色なら `(0.5, 0.5, 0.5)`）
- → **BaseColor** に接続。
- 色をエディタで変えたい場合は `VectorParameter` にしてもよい。

---

### E. BPインスタンスへの割当

1. `AErasableWall` の `VisualMesh` の **マテリアルスロット 0** に `M_Basic_Wall_Vanish` を設定する。
2. C++ の `ColoursConeLight::ApplyMIDParams()` が `CreateAndSetMaterialInstanceDynamic(0)` で自動的に MID 化してキャッシュするため、ユーザーがパラメータ値を手入力する必要はない。

---

### F. デバッグ手順

#### 症状A — 壁が全く透明にならない（コーンを当てても何も変化しない）

**Step A-1** `Active` ScalarParameter を **EmissiveColor** に差し替えて PIE で壁が光るか確認。
- 光る → `Active` は届いている。C++ から `ApplyMIDParams` が呼ばれているか確認（`ColoursConeLight` がワールドに配置済みか）。
- 光らない（真っ黒）→ MID が作られていない。`VisualMesh` のスロット 0 に `M_Basic_Wall_Vanish` が割り当てられているか確認。

**Step A-2** `Active` の **Parameter Name** を Detail パネルで確認。末尾スペースや大文字/小文字のズレがないか1文字ずつ照合。

---

#### 症状B — コーンに入っても一部しか消えない／ズレる

**Step B-1** `LightPos` を EmissiveColor に差し替え（Divide(÷1000) してスケール調整）。PIE で何らかの色が見えれば値は届いている。黒なら `LightPos` パラメータ名の綴りミス。

**Step B-2** `LightDir` を EmissiveColor に直結。コーンが +X 向きなら赤 (1,0,0) 系が見えるはず。黒なら綴りミス。

**Step B-3** `CosConeAngle` を EmissiveColor に直結（float → float3 へ `Append` または `Constant3Vector` 経由）。PIE で 0 より大きな値が見えるはず。0 のまま → 全方向がコーン内判定になり壁が全消え（または `CosConeAngle` 名のズレ）。

---

#### 症状C — Active が届いているのにコーンを当てると逆に壁が出現する

`If` ノードの A/B ピンが逆（`cosAngle < CosConeAngle` を True にしている）。  
④・⑥ の `If` の A≥B=TrueSide を再確認。

---

> **再発防止推奨**: 純ノードグラフ版は `If` の引数順ミスが多い。計算全体を **C-1 の Custom ノード 1 個**に集約すると入力ピン 6 本＋ 5 行 HLSL のみになり事故が起きにくい。
