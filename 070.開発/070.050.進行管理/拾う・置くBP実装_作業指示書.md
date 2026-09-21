---
tags: [Colours, 作業指示書, Blueprint, インタラクト]
project: Colours
updated: 2026-09-21
---

# 作業指示書: 拾う・置くBP実装

## 1. 概要

M2で使う汎用の「拾うアクション」「置くアクション」を実装する。

オブジェクト側には `UColoursInteractableComponent` 派生の `BPC_PickupPlace` を1個持たせる。  
Jiraでは「拾うアクション」「置くアクション」を別Taskとして扱うが、BP Componentは分けない。

所持物の管理はプレイヤー側の「所持状態管理」を使用する。

## 2. 終了条件

### 拾うアクション

- [ ] `BPC_PickupPlace` を持つActorへF入力すると、対象Actorがプレイヤーの所持Actorになる
- [ ] 既に所持Actorがある場合、2個同時所持にならない

### 置くアクション

- [ ] 所持中のActorに対して `Place` を実行すると、プレイヤーの所持状態が解除される
- [ ] Actorが保持先から外れる
- [ ] 手を離した時点の向きを維持する
- [ ] Physicsが有効になり、落下を開始する

## 3. 関係する仕様

- [[050.仕様/050.020.プレイヤー/020.005.インタラクト/インタラクト.040.実装|インタラクト — 実装]]
- [[050.仕様/050.020.プレイヤー/020.010.モノを拾う/モノを拾う.020.仕様|モノを拾う — 仕様]]
- [[050.仕様/050.020.プレイヤー/020.010.モノを拾う/モノを拾う.040.実装|モノを拾う — 実装]]
- [[050.仕様/050.020.プレイヤー/020.020.モノを置く/モノを置く.020.仕様|モノを置く — 仕様]]
- [[050.仕様/050.020.プレイヤー/020.020.モノを置く/モノを置く.040.実装|モノを置く — 実装]]
- [[010.規約/アセット命名規約|アセット命名規約]]

## 4. 対象とするファイル・アセット、つくるファイル・アセット

### 対象

- プレイヤーの「所持状態管理」
- 拾う／置く動作を確認するテストActor

### 作成

- `BPC_PickupPlace`
  - 親クラス: `UColoursInteractableComponent`
  - 配置: `Content/Common/Interaction/`

## 5. 作業手順

1. `Content/Common/Interaction/` に `BPC_PickupPlace` を作成し、親クラスを `UColoursInteractableComponent` にする。
2. `PerformInteraction` をOverrideする。
3. `Interactor` の所持状態を取得し、未所持なら `GetOwner()` を所持Actorとして設定する。
4. 所持に成功した場合は `PerformInteraction` から `true` を返す。
5. `BPC_PickupPlace` に `Place(Interactor) -> bool` を作成する。
6. `Place` で、現在の所持Actorが `GetOwner()` であることを確認する。
7. プレイヤーの所持状態を解除する。
8. `GetOwner()` を Keep World Transform でDetachする。
9. 手を離した時点のWorld Rotationを維持したまま、対象の物理Componentの Simulate Physics を有効にする。
10. テストActorに `IColoursInteractable` と `BPC_PickupPlace` を設定する。
11. PIEで「拾うアクション」の終了条件を確認する。
12. PIEで「置くアクション」の終了条件を確認する。
