# Step2 実装ログ: ライントレース検知

## 実装日
2026-06-13

## 対応バックログ
[[要チケット化リスト]] > Step2

---

## 実装方針

`PerformConeTrace()` 内で ForwardVector を `ConeAngleDeg` の範囲内で等分した方向へ `NumTraces` 本 `LineTraceByChannel` を放射。`HitActor` と `ImpactPoint` を取得。

- Timer 周期: 0.05s（20fps 相当）から開始、負荷を見て調整
- まず水平扇のみ実装、余力で縦横グリッドに拡張

## 完了条件（達成済み）
ヒット座標が `UE_LOG` または `PrintString` でログに出る最小実装ができている。
