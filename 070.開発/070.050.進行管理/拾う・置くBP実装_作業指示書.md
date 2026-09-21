---
tags: [Colours, 作業指示書, Blueprint, インタラクト]
project: Colours
updated: 2026-09-21
---

# 作業指示書: 所持・拾う・置くBP実装

## 1. 概要

M2で使う「所持状態管理」「拾うアクション」「置くアクション」を実装する。

プレイヤーは現在の所持Actorを1個だけ管理する。  
拾う／置く処理は、オブジェクト側の `UColoursInteractableComponent` 派生 `BPC_PickupPlace` に実装する。

Jiraでは「所持状態管理」「拾うアクション」「置くアクション」を別Taskとして扱う。

## 2. 終了条件

### 所持状態管理

- [ ] 未所持状態では所持Actorが `None`
- [ ] 未所持状態からActorを1個所持状態にできる
- [ ] 所持中に別Actorを設定しようとしても2個同時所持にならない
- [ ] 所持Actorを解除すると `None` に戻る

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

- `Content/Colours/Character/BP_ColoursPlayerCharacter.uasset`
  - 所持状態管理を追加する
- `Content/Colours/Gimmick/BP_TestInteractable.uasset`
  - 拾う／置く動作の確認用Actor
- `Content/Colours/Gimmick/BPC_TestInteract.uasset`
  - `UColoursInteractableComponent` 派生BPの既存実装例
- `Content/Colours/Levels/Test/ThirdPersonMap.umap`
  - PIE確認に使用する

### 作成

- `Content/Colours/Gimmick/BPC_PickupPlace.uasset`
  - 親クラス: `UColoursInteractableComponent`

## 5. 作業手順

### 5.1 `Content/Colours/Character/BP_ColoursPlayerCharacter.uasset` — `HeldActor` プロパティ

1. Actor Object Reference 型の変数 `HeldActor` を追加する。
2. 初期値を `None` にする。
3. Compileして保存する。

### 5.2 `Content/Colours/Character/BP_ColoursPlayerCharacter.uasset` — `GetHeldActor`

1. `GetHeldActor() -> Actor` 関数を追加する。
2. `HeldActor` をそのまま返す。
3. Pure Functionにする。
4. Compileする。

### 5.3 `Content/Colours/Character/BP_ColoursPlayerCharacter.uasset` — `TrySetHeldActor`

1. `TrySetHeldActor(NewHeldActor) -> bool` 関数を追加する。
2. `NewHeldActor` が有効か確認する。
3. `HeldActor` が `None` であることを確認する。
4. 両方を満たす場合だけ `HeldActor = NewHeldActor` を設定する。
5. 設定できた場合は `true`、設定できない場合は `false` を返す。
6. Compileする。

### 5.4 `Content/Colours/Character/BP_ColoursPlayerCharacter.uasset` — `ClearHeldActor`

1. `ClearHeldActor(ExpectedActor) -> bool` 関数を追加する。
2. 現在の `HeldActor` と `ExpectedActor` が一致するか確認する。
3. 一致する場合だけ `HeldActor` を `None` にする。
4. 解除できた場合は `true`、解除しなかった場合は `false` を返す。
5. Compileして保存する。

### 5.5 `Content/Colours/Gimmick/BPC_PickupPlace.uasset` — アセット作成・親クラス設定

1. `Content/Colours/Gimmick/` に Blueprint Component を作成する。
2. 名前を `BPC_PickupPlace` とする。
3. 親クラスに `UColoursInteractableComponent` を指定する。
4. Compileし、`PerformInteraction` をOverrideできることを確認する。

### 5.6 `Content/Colours/Gimmick/BPC_PickupPlace.uasset` — `PerformInteraction`

1. `PerformInteraction` をOverrideする。
2. `Interactor` を `BP_ColoursPlayerCharacter` として扱えることを確認する。
3. プレイヤーの `TrySetHeldActor` に `GetOwner()` を渡す。
4. `TrySetHeldActor` の戻り値を `PerformInteraction` の戻り値として返す。
5. Compileする。

### 5.7 `Content/Colours/Gimmick/BPC_PickupPlace.uasset` — `Place`

1. Blueprint Callable の `Place(Interactor) -> bool` 関数を追加する。
2. `Interactor` を `BP_ColoursPlayerCharacter` として扱えることを確認する。
3. プレイヤーの `GetHeldActor` が `GetOwner()` と一致することを確認する。
4. プレイヤーの `ClearHeldActor` に `GetOwner()` を渡す。
5. `GetOwner()` のWorld Transformを保持したまま、保持先からDetachする。
6. Detach前のWorld Rotationを維持する。
7. 対象Actorの物理挙動を担当するComponentの Simulate Physics を有効にする。
8. 正常に置く処理を開始できた場合は `true` を返す。
9. Compileする。

### 5.8 `Content/Colours/Gimmick/BP_TestInteractable.uasset` — テストActor設定

1. `IColoursInteractable` が実装されていることを確認する。
2. 既存の `BPC_TestInteract` を外し、`BPC_PickupPlace` を1個追加する。
3. プレイヤーのインタラクト判定に入るCollisionが有効であることを確認する。
4. Compileして保存する。

### 5.9 `Content/Colours/Levels/Test/ThirdPersonMap.umap` — 所持状態管理・拾うアクション確認

1. `BP_TestInteractable` を2個配置する。
2. PIE開始時にプレイヤーの `HeldActor` が `None` であることを確認する。
3. 1個目をインタラクト候補にしてFキーを押す。
4. `HeldActor` が1個目のActorになることを確認する。
5. 2個目へFキーを押し、`HeldActor` が1個目のままであることを確認する。
6. `ClearHeldActor` を実行し、`HeldActor` が `None` に戻ることを確認する。

### 5.10 `Content/Colours/Levels/Test/ThirdPersonMap.umap` — 置くアクション確認

1. テストActorをFキーで拾い、プレイヤーの所持Actorにする。
2. テスト用に `BPC_PickupPlace.Place` を呼び出す。
3. プレイヤーの `HeldActor` が `None` になることを確認する。
4. 対象Actorが保持先からDetachされることを確認する。
5. Detach前後でWorld Rotationが変わらないことを確認する。
6. Simulate Physicsが有効になり、Actorが落下を開始することを確認する。
7. 「所持状態管理」「拾うアクション」「置くアクション」の終了条件をすべて確認する。
