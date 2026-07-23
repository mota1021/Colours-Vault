---
tags: [Colours, AIエージェント, 実行計画]
project: Colours
created: 2026-07-23
jira: SCRUM-73
---

# 実行計画: CS-5 光源形状非依存化アーキテクチャ

> Jira: SCRUM-73（CS-5）／親 SCRUM-5／担当 森／先行 SCRUM-12(CS-3)・SCRUM-19(EW-1)・SCRUM-70(SP-16)
> 仕様正本: [[伝播.040.実装]]「形状非依存化アーキテクチャ」「判定フロー」／[[伝播.020.仕様]]

## 背景・問題

現状、光源（`AColoursConeLight`）が壁セル中心のコーン内外（角度＋距離）を**光源側で計算**し `Wall->SetSegmentEnabled()` を駆動している（`ColoursConeLight::UpdateErasableWallSegments()`）。さらに壁は `UpdateConeSection(LightPos, LightDir, CosConeAngle, Range, ...)` でコーン固有パラメータを受け取っており、**壁がコーン形状を知っている**状態。

仕様040が求める到達点は「光源が①形状判定『点は光の中か』②概形バウンズ③色 を提供し、壁はセル分割・消去・復活のみを持ち形状の数学を一切持たない」。実現機構は**光源基底クラスの仮想関数**（Cone／Beam／Flame が各自の形状判定を実装）とする。

## 完了定義

- **Must**: 壁がコーン固有パラメータを**判定目的で**受け取らず、光源基底の形状判定経由で既存のコーン消去が同等動作する。Cone の形状判定が `virtual` 実装として基底経由で呼ばれる。色が壁へ passthrough で届く。
- **ストレッチ**: Beam／Sphere の `virtual` 実装スタブ（各1関数の空/仮実装）を用意し、将来光源の追加点を明示する。

## 契約API（光源基底が提供）

- `virtual bool IsPointLit(const FVector& Point) const` — コーン=角度+距離／直線=カプセル内／球=距離のみ
- `virtual FBox GetLightBounds() const` — 対象の壁を絞る概形バウンズ
- `virtual FColoursLightValue GetLightValueAt(const FVector& Point) const` — その点に届く色

---

## Task 1: 光源基底クラス新設＋契約API定義

**対象ファイル**: `Source/Colours/Public/Gimmick/ColoursLightSourceBase.h`（新規）／同 `Private/.../ColoursLightSourceBase.cpp`（新規）

**作業内容**:
- `AColoursLightSourceBase`（`AActor` 派生）を新設し、上記契約API 3種を `virtual` 宣言する。
- 既存C++基底クラス方針（`FColoursColorBase` の static 集約と同じ思想）と地続きにする。

**完了条件**: 基底クラスがコンパイルし、既存クラスに影響を与えない。

---

## Task 2: `AColoursConeLight` を基底派生へ移行＋コーン形状判定を virtual 実装へ移設

**対象ファイル**: `Source/Colours/Public/Gimmick/ColoursConeLight.h`／`Private/Gimmick/ColoursConeLight.cpp`

**作業内容**:
- `AColoursConeLight` の継承を `AColoursLightSourceBase` へ変更。
- `UpdateErasableWallSegments()` 内のコーン内外計算（`CosA > CosConeAngle && Dist < Range`）を `IsPointLit` の Cone 実装として移設。
- `GetLightBounds` はコーンの射程・角度から算出。`GetLightValueAt` は `LightColor`／`Intensity` から `FColoursLightValue` を返す。

**完了条件**: 既存のコーン消去が基底経由 `IsPointLit` で同等に動作する（回帰なし）。

---

## Task 3: 判定所有権の移設（壁から形状の数学を除去）

**対象ファイル**: `Source/Colours/Public/Gimmick/ErasableWall.h`／`Private/Gimmick/ErasableWall.cpp`、`Private/Gimmick/ColoursConeLight.cpp`

**作業内容**:
- 壁は**セル一覧（中心座標）を公開する API** のみ持つ（`GetSegmentCenter`/`GetSegmentCount` は既存。列挙導線を整理）。
- 光源が各セル中心を `IsPointLit` で判定して `SetSegmentEnabled` を駆動する構造へ移す（判定フロー: 光源が範囲内の壁を `GetLightBounds` で絞る→壁からセル一覧→`IsPointLit`→通知）。
- 壁の判定用途からコーン固有パラメータ授受を切り離す。
- **視覚断面プラグ（`ConeSectionPlug`／`UpdateConeSection`）はコーン専用のまま残す**（決定2の線引き＝判定レイヤのみ非依存化・視覚は別レイヤ）。視覚の形状非依存化はバックログ済み（`要チケット化リスト.md` インボックス 2026-07-23）。

**完了条件**: 壁が `CosConeAngle`／`Range` を**判定目的で**受け取らずに消去が動作する。

---

## Task 4: 色 passthrough 経路

**対象ファイル**: `Private/Gimmick/ColoursConeLight.cpp`／`Public/Gimmick/ErasableWall.h`

**作業内容**:
- `GetLightValueAt` の色を「(セルindex, 色)」として壁へ通知する経路を通す。
- 壁側の色照合（`FColoursColorBase::IsColorMatch`）→消去ゲートは **EW-5（色ゲート統合）のスコープ**。本Taskでは壁が色を受領するところまで（passthrough）。

**完了条件**: 壁が色（`FColoursLightValue`）を受領できる（照合・消去接続は EW-5 で行う）。

---

## 実施順序

Task 1 → Task 2 → Task 3 → Task 4（直列。Task 2 は Task 1 の契約に依存、Task 3/4 は Task 2 の Cone 実装に依存）

## 依存・申し送り

- **CS-3（SCRUM-12 照合）はソフト依存**: 中核の `FColoursColorBase::IsColorMatch` は実装済みのため、CS-3 チケット完了を待たず本計画を進められる。
- **EW-5 見直し（検討メモ申し送り#6）**: Task 3/4 で壁インターフェースが「セル公開＋色通知」に変わると、EW-5（色ゲート統合）の接続先が変わり、`EW-5色ゲート統合_実行計画.md` の該当 Task 見直しが要る可能性。
- **事前判断（ユーザー）**: 併存プロト `DynamicErasableWall` を本移設に含めるか、`ErasableWall` 本系のみ対象にするか。
- **Jira 依存リンク**: CS-4↔CS-5 は Jira 上リンクなし（並行可）だが、CS-4 が本計画の形状判定契約を消費するため実装上は **CS-5 先行**。依存リンク付与の要否は着手時にユーザー確認。
