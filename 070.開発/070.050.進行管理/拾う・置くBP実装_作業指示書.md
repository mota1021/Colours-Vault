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

### 5.1 `BPC_PickupPlace` を作成する

1. `Content/Common/Interaction/` に Blueprint Component を作成する。
2. 名前を `BPC_PickupPlace` とする。
3. 親クラスに `UColoursInteractableComponent` を指定する。
4. Compileして、`PerformInteraction` をOverrideできることを確認する。

### 5.2 拾うアクションを実装する

1. `PerformInteraction` の `Interactor` から、プレイヤー側の「所持状態管理」を取得する。
2. 現在の所持Actorを取得する。
3. 所持Actorが空の場合、`GetOwner()` を新しい所持Actorとして設定する。
4. 所持設定に成功した場合は `true`、失敗した場合は `false` を返す。
5. テストActorを作成または既存Actorを使用し、以下を設定する。
   - `IColoursInteractable` を実装する
   - `BPC_PickupPlace` を1個追加する
   - プレイヤーのインタラクト判定に入るCollisionを持たせる
6. PIEを開始し、対象Actorがインタラクト候補として選択されることを確認する。
7. Fキーを押し、`PerformInteraction` が実行されることを確認する。
8. プレイヤーの所持Actorが対象Actorになっていることを確認する。
9. 既に所持Actorがある状態でもう一度別Actorを拾おうとし、2個同時所持にならないことを確認する。

### 5.3 `Place` を作成する

1. `BPC_PickupPlace` に Blueprint Callable の `Place` 関数を追加する。
2. 引数に `Interactor`、戻り値に `bool` を持たせる。
3. `Interactor` から「所持状態管理」を取得する。
4. 現在の所持Actorを取得し、`GetOwner()` と一致していることを確認する。
5. 一致している場合、現在の所持Actorを解除する。
6. `GetOwner()` の現在のWorld Transformを保持したまま、保持先からDetachする。
7. Detach直前のWorld Rotationを保存し、Detach後も同じ向きを維持する。
8. 対象Actorで物理挙動を担当するComponentに対して Simulate Physics を有効にする。
9. 正常に置く処理を開始できた場合は `true` を返す。

### 5.4 置くアクションを確認する

1. テストActorをプレイヤーの所持Actorにする。
2. テスト用に `Place` を呼び出す。
3. 実行後、プレイヤーの所持Actorが空になっていることを確認する。
4. Actorが保持先からDetachされていることを確認する。
5. Detach前後でWorld Rotationが変わっていないことを確認する。
6. Simulate Physicsが有効になり、Actorが落下を開始することを確認する。
7. 「拾うアクション」「置くアクション」の終了条件をすべて満たしたら、それぞれのJira Taskへ確認結果を記録する。
