# Step3 実装ログ: ヒット壁へパラメータ受け渡し

## 実装日
2026-06-13

## 対応バックログ
[[要チケット化リスト]] > Step3

---

## 実装方針

`PerformConeTrace()` のヒット結果から `HitWallMIDs` を更新。

- 新規ヒット壁: `CreateDynamicMaterialInstance` → Map に追加し `Active=1` で各パラメータを Set
- 当フレームのヒット集合から外れた壁: `Active=0` に戻す（`LightPos` 等はそのまま残す）

### MID に渡すパラメータ
`LightPos` / `LightDir` / `CosConeAngle` / `Range` / `Active`

## 完了条件（達成済み）
ライトを向けた壁の MID パラメータが更新され、向きを外すと `Active` が戻ることをログ／デバッグ表示で確認できる。
