# Step1 実装ログ: C++ 基底クラス `AColoursConeLight`

## 実装日
2026-06-13

## 対応バックログ
[[実装バックログ]] > Step1

---

## 実装方針

BP ではなく C++ で基底クラスを作り、BP_ConeLight はその子クラスにする。

### コンポーネント構成
- `USpotLightComponent* SpotLight`（Root）
- `UStaticMeshComponent* ConeCollisionMesh`（SpotLight にアタッチ）
- 両方とも `UPROPERTY(VisibleAnywhere)`

### 公開プロパティ（`EditAnywhere, BlueprintReadWrite`）
| プロパティ | 型 | デフォルト |
|---|---|---|
| `ConeAngleDeg` | float | 30 |
| `Range` | float | 1000 |
| `LightColor` | FLinearColor | White |
| `NumTraces` | int32 | 7 |

### 設計上の決定
- ライントレース更新は Tick ではなく `FTimerHandle` で間引く（`PerformConeTrace()` を `UFUNCTION(BlueprintCallable)`）
- ヒット壁 → MID のキャッシュは `TMap<AActor*, UMaterialInstanceDynamic*> HitWallMIDs`（`UPROPERTY()` で GC 保護）
- BP 拡張フックとして `OnWallHit(AActor*, FVector)` / `OnWallReleased(AActor*)` を `BlueprintImplementableEvent` で定義
- MID への Set 処理と `Active=0` の解放処理は C++ 内に実装

## 完了条件（達成済み）
UE でコンパイルが通り、レベルに置いて Details から `ConeAngleDeg`/`Range` を変更できる。
