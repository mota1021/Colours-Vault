---
tags: [Colours, AIエージェント, 実行計画]
project: Colours
created: 2026-07-11
---

# 実行計画: EW-5 色ゲート統合

> **実装担当への前提**: 本計画は 2026-07-11 に Fable（計画セッション）がユーザーと合意済み。**確定済み決定事項（§決定事項）を再質問しない**こと。コードの行番号は調査時点のもの——編集前に必ず該当ファイルを読んで現物を確認する。

## 背景・問題

- EW-1 で「光が当たっている間だけ消える壁」（`AErasableWall`）は実装済みだが**色非依存**（どんな色の光でも消える）。
- 仕様（`shared/050.仕様/050.030.ギミック/030.020.消える壁/020.020.仕様.md`）は「**光の色と壁の色が同じ場合に消える**／異なる色の光は壁を消さない」。
- 照合ロジック自体は CS-3 で実装済み: `FColoursColorBase::IsColorMatch(RgbA, RgbB, Threshold)`（RGB正規化→ユークリッド距離 d ≦ しきい値。`Source/Colours/Public/ColourType/ColoursColorBase.h:15`）。※チケット原案の「DoColoursMatch」という関数名は存在しない。
- 現状、**色情報が両端に欠けている**: ライト `AColoursConeLight` は見た目用 `FLinearColor LightColor` のみ、壁 `AErasableWall` は色プロパティなし。
- EW-5 は MVP クリティカルパス上（CS-1→CS-3→**EW-5**→MVP-LV→MVP-GE）。後続の MVP-LV・LV-3・LV-4 がブロックされている。

## 完了定義

- **Must（= Jira DoD・週目標）**: 新規テストマップの PIE で ①赤ライト→赤壁が**消える** ②青ライト→赤壁が**消えない** ③光を外すと**復活する**。
- **ストレッチ**: 青壁も配置して対称確認（赤ライト→青壁が消えない／青ライト→青壁が消える）。

## 決定事項（2026-07-11 ユーザー確定・再質問不要）

| # | 論点 | 決定 |
|---|---|---|
| 1 | 色ゲート対象 | **AErasableWall のみ**。`ADynamicErasableWall` は色非依存のまま**一切変更しない** |
| 2 | 差込方式 | **ライト側・壁単位ゲート**（判定主体がライトである現行構造に沿う） |
| 3 | ライトの色 | `FColoursRGBValue`（旧 LightValue）プロパティに**一元化**。見た目の SpotLight 色は `GetBaseColour()` から**導出**（旧 `FLinearColor LightColor` は廃止） |
| 4 | 壁の色 | `FColoursCMYValue`（旧 InkValue）を使用 |
| 5 | しきい値 | **カラーシステム用 DataAsset** を新設して保持。初期値 **0.3f** |
| 6 | 型改名 | FColoursColorBase→**FColoursColourBase** / FColoursLightValue→**FColoursRGBValue** / FColoursInkValue→**FColoursCMYValue**（ファイル名も） |
| 7 | 関数改名 | ColorDistance→**ColourDistance** / IsColorMatch→**IsColourMatch** / GetBaseColor→**GetBaseColour** / GetLightValue→**GetRGBValue** / GetInkValue→**GetCMYValue** |
| 8 | PIE確認 | **新規テストマップ**を作成（既存マップ流用しない） |
| 9 | 仕様書の用語更新 | **スコープ外**（「インク型→CMY型」等の仕様側改名は別途仕様セッションで判断。仕様書を書き換えないこと） |
| 10 | 役割分担 | C++実装 = AI／エディタ作業（アセット・マップ作成・配置・PIE確認）= ユーザー |

## 実行環境

- **コード**: `E:\UEProjects\Colours`（UEプロジェクト。Vault とは別リポジトリ）
- **エンジン**: **UE5.8**（2026-07-08 に 5.3 から移行済み。`Colours.uproject` の EngineAssociation を確認）
- **ビルド**: VS2022 / Development Editor / Win64。コマンドラインなら `<UE5.8インストール先>\Engine\Build\BatchFiles\Build.bat ColoursEditor Win64 Development -Project="E:\UEProjects\Colours\Colours.uproject" -WaitMutex`
- **VCS**: E: 側は **Diversion (dv)**（デスクトップクライアント起動が前提。`cd E:\UEProjects\Colours` してから dv コマンド）。Vault 側は git。セッション末は `/colours-end` で**両方コミット**
- **主要ソース**: `E:\UEProjects\Colours\Source\Colours\{Public,Private}\ColourType\`・`\Gimmick\`

## 現状コードの要点（調査済み 2026-07-11）

- 型: `FColoursColourBase`（基底・フィールドなし・static 変換/照合のみ）、`FColoursLightValue`（R/G/B int32 + Intensity + DamageValue、`GetRGB()` あり）、`FColoursInkValue`（C/M/Y + DamageMax、`GetRGB()` あり）※名前は改名前
- 消去判定の主体は**ライト側** `AColoursConeLight`（`Private/Gimmick/ColoursConeLight.cpp`）:
  - `BeginPlay` が `PerformConeTrace` を **0.05秒(20Hz)タイマー**で起動（cpp:43-49 付近）
  - `PerformConeTrace`（cpp:111-219 付近）: ライントレース（`ECC_GameTraceChannel2`）で `CurrentHitActors` を収集 → `UpdateErasableWallSegments(CurrentHitActors)`・`UpdateDynamicErasableWalls(CurrentHitActors)` を呼ぶ → 前フレームにあって今回ない壁を `RestoreAllSegments()` / `RestoreMesh()` で復元（cpp:192-216 付近）
  - `UpdateErasableWallSegments`（cpp:236-262 付近）: 各 `AErasableWall` のセグメント中心を幾何コーン判定（`CosA > CosConeAngle && Dist < Range`）し `SetSegmentEnabled(!bInCone)` ← **AErasableWall の消去条件の実体**
  - `Tick`（cpp:83-109 付近）: ヒット中の壁のマテリアル・断面プラグ（`UpdateConeSection`）を毎フレーム視覚更新
- `AErasableWall`（`Private/Gimmick/ErasableWall.cpp`）: `SetSegmentEnabled`（cpp:219-224）・`RestoreAllSegments`（cpp:232-241）・`UpdateConeSection`（cpp:243-268、見た目のみ）

---

## Task 1: 型・関数リネーム（先行整備。機能変更と混ぜない）

**対象ファイル**: `Source/Colours/{Public,Private}/ColourType/ColoursColorBase.{h,cpp}`・`ColoursLightValue.{h,cpp}`・`ColoursInkValue.{h,cpp}`＋これらを参照する全ファイル、`Config/DefaultEngine.ini`

**作業内容**:
1. リネーム対応表どおりに型名・ファイル名・関数名を変更（§決定事項 #6・#7）。ファイル名変更に伴い `#include "ColourType/XXX.h"` と `#include "XXX.generated.h"` の行も全て更新（.generated.h の名前はヘッダファイル名と一致が必須）
2. 参照箇所の洗い出し: `Source/Colours` 配下を `ColoursColorBase|ColoursLightValue|ColoursInkValue|ColorDistance|IsColorMatch|GetBaseColor|GetLightValue|GetInkValue` で grep し全置換（UE標準の `FColor`/`FLinearColor` を巻き込まないこと）
3. `Config/DefaultEngine.ini` に追記（BPアセットが旧構造体名を参照していても読めるようにする。redirect 名に F プレフィックスは付けない）:
   ```ini
   [CoreRedirects]
   +StructRedirects=(OldName="/Script/Colours.ColoursColorBase",NewName="/Script/Colours.ColoursColourBase")
   +StructRedirects=(OldName="/Script/Colours.ColoursLightValue",NewName="/Script/Colours.ColoursRGBValue")
   +StructRedirects=(OldName="/Script/Colours.ColoursInkValue",NewName="/Script/Colours.ColoursCMYValue")
   ```
   ※ 関数（非UFUNCTION の純C++メソッド）に redirect は不要
4. ビルド → ユーザーにエディタ起動を依頼し、既存テストマップ（`Content/Colours/Levels/Test/ColourParameterTest`・`LightParameterTest`）を開いて Output Log にロードエラーがないこと・従来挙動（色非依存の消去）を確認

**完了条件**: ビルドがエラー0で通過し、既存テストマップが正常にロード・動作する

---

## Task 2: カラーシステム設定 DataAsset

**対象ファイル**: `Source/Colours/Public/ColourType/ColoursColourSystemAsset.h`（新規）＋対応 .cpp

**作業内容**:
```cpp
UCLASS(BlueprintType)
class COLOURS_API UColoursColourSystemAsset : public UDataAsset
{
    GENERATED_BODY()
public:
    /** 色一致判定のしきい値（RGB正規化ユークリッド距離、値域 0〜√3） */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Colour")
    float ColourMatchThreshold = 0.3f;
};
```
- ビルド後、**ユーザー操作**: エディタで `Content/Colours/Data/DA_ColourSystem` としてアセットを1つ作成（場所・名前を変える場合は Task 3 の既定パスも合わせる）

**完了条件**: ビルド成功。アセットが存在し Threshold=0.3 がエディタで編集可能

---

## Task 3: ライトに色を持たせる（LightValue 一元化）

**対象ファイル**: `Source/Colours/Public/Gimmick/ColoursConeLight.h`・`Private/Gimmick/ColoursConeLight.cpp`

**作業内容**:
1. プロパティ追加:
   ```cpp
   /** このライトの色（判定・見た目の単一ソース） */
   UPROPERTY(EditAnywhere, Category = "Colour")
   FColoursRGBValue LightValue;

   /** カラーシステム共通設定（しきい値） */
   UPROPERTY(EditAnywhere, Category = "Colour")
   TObjectPtr<UColoursColourSystemAsset> ColourSettings;
   ```
   コンストラクタで `ConstructorHelpers::FObjectFinder` により既定アセット `/Game/Colours/Data/DA_ColourSystem` を設定（見つからなければ nullptr のままで可）
2. 既存 `FLinearColor LightColor`（ColoursConeLight.h:31 付近）を**削除**し、参照箇所（SpotLight への色適用・コーン視覚のマテリアル色等、grep で全箇所特定）を `LightValue.GetBaseColour()` 由来に置換
3. `OnConstruction` で SpotLight 色へ反映（配置時にエディタで見た目確認できるように）。BeginPlay でも適用
4. しきい値取得ヘルパを追加: `float GetColourMatchThreshold() const`（`ColourSettings` が null なら 0.3f フォールバック＋初回のみ Warning ログ）

**完了条件**: ビルド成功。エディタでライトの R/G/B を変えると SpotLight の見た目色が追従する
**注意**: 既存マップに配置済みライトの旧 LightColor 設定値は失われる（テスト用マップのみ・ユーザーが再設定）

---

## Task 4: 壁に色を持たせ、色ゲートを差し込む

**対象ファイル**: `Source/Colours/Public/Gimmick/ErasableWall.h`・`Private/Gimmick/ColoursConeLight.cpp`

**作業内容**:
1. `AErasableWall` にプロパティ追加:
   ```cpp
   /** 壁の色。ライトの色と一致した場合のみ消える（仕様: 消える壁 020） */
   UPROPERTY(EditAnywhere, Category = "Colour")
   FColoursCMYValue WallColour;
   ```
2. `AColoursConeLight` に壁単位の色ゲートを実装:
   ```cpp
   const bool bMatch = FColoursColourBase::IsColourMatch(
       LightValue.GetRGB(), Wall->WallColour.GetRGB(), GetColourMatchThreshold());
   ```
   **推奨挿入点**: `PerformConeTrace` 内で `CurrentHitActors` 確定直後に、`AErasableWall` のみ色照合でフィルタし「不一致の壁は当たっていない」扱いにする。こうすると (a) セグメント消去がスキップされ (b) 既消去分は既存の Prev/Current 差分復元パスが自動で戻し (c) `Tick` の断面プラグ・マテリアル視覚も不一致壁に出なくなる。
   **実装前に必ず** `Tick` の視覚更新と復元パスがどの集合（`CurrentHitActors`/`PrevHitActors`）を参照しているか現物確認し、フィルタ位置がその全てに効くことを確かめること。効かない構造だった場合の代替: `UpdateErasableWallSegments` 冒頭で不一致壁を `RestoreAllSegments()`＋skip し、視覚側にも同じガードを入れる。
3. `ADynamicErasableWall` と `UpdateDynamicErasableWalls` は**変更しない**

**完了条件**: ビルド成功。コード上「不一致→消えない（視覚も出ない）／一致→従来どおり消える／光が外れる→復活」の3経路が成立

---

## Task 5: 新規テストマップで PIE 確認（= DoD。ユーザー作業）

**対象**: `Content/Colours/Levels/Test/ColourGateTest.umap`（新規・ユーザーがエディタで作成）

**配置と設定値**:

| アクター | 設定 |
|---|---|
| 赤壁（AErasableWall） | WallColour: **C=0, M=255, Y=255**（DamageMax=255 のまま → RGB(255,0,0) 相当） |
| 赤ライト（AColoursConeLight） | LightValue: **R=255, G=0, B=0** |
| 青ライト（AColoursConeLight） | LightValue: **R=0, G=0, B=255** |
| （ストレッチ）青壁 | WallColour: **C=255, M=255, Y=0**（RGB(0,0,255) 相当） |

**完了条件（そのまま DoD チェックリスト）**:
- [ ] 赤ライトを赤壁に向ける → 照射部分が消え、通り抜けられる
- [ ] 青ライトを赤壁に向ける → 消えない（断面プラグ等の消去視覚も出ない）
- [ ] 赤ライトを外す → 壁が復活する
- [ ] （ストレッチ）青壁で対称確認

---

## Task 6: 完了処理

**作業内容**:
1. Jira: JQL `project = SCRUM AND labels = "元ID:EW-5"` でチケットを特定し「完了」へ遷移（**REST API スクリプト**で実施。認証は `D:\document\ObsidianVault\.env`、依存は requests のみ、遷移「完了」= transition id **51**。単発なので scratchpad スクリプトで可。参考実装: `shared/900.AIエージェント用/scripts/jira_sp_snapshot.py` の .env パースと API 呼び出し）
2. 実装ログ作成: `shared/070.開発/070.040.実装ログ/260712.EW-5色ゲート統合.md`（既存ログの体裁に合わせ、変更ファイル・設計判断・PIE確認結果を記録）
3. セッション終了時は `/colours-end`（今日やる事アーカイブ・現在地再生成・**git と dv の二重コミット**）

**完了条件**: Jira の EW-5 が「完了」・実装ログが存在・両リポジトリにコミット済み

---

## 実施順序

Task 1 → 2 → 3 → 4 →（ユーザー: アセット作成は Task 2 後・マップ作成は Task 4 後）→ Task 5 → Task 6
※ Task 1 は独立した純リネーム。Task 3・4 は Task 1・2 に依存。各 Task 完了ごとにビルド確認。

## 想定される難所

- **CoreRedirects の網羅漏れ**: BP アセットが旧構造体名を参照しているとロード失敗 → Task 1 完了条件（既存マップを開いて確認）で検出
- **`.generated.h` の名前不一致**: ヘッダファイル名変更時に include 名の更新漏れがあるとビルド不能 → grep で機械的に確認
- **色ゲートのフィルタ位置**: 視覚更新・復元パスに効かない位置に入れると「消えないのに断面プラグが出る」等のちぐはぐが起きる → Task 4 の現物確認手順を踏む
- **複数ライト同時照射のセグメント競合**: 既存制約（MVPは1灯）。**今回は直さない**・挙動を変えない

## 検証方法（エンドツーエンド）

1. 各 Task 後: Development Editor / Win64 ビルドがエラー0
2. Task 1 後: 既存テストマップのロード・従来挙動維持（リグレッションなし）
3. Task 5: ColourGateTest で DoD チェックリスト全項目（ユーザーの PIE 操作で確認）
4. Task 6: Jira 遷移の API レスポンス確認・`/colours-end` の完了
