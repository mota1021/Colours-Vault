---
tags: [Colours, 作業指示書, Blueprint, インタラクト]
project: Colours
updated: 2026-09-21
---

# 拾う・置くBP実装 — 作業指示書

## 目的

M2で使う汎用の「拾う」「置く」を、オブジェクト側のBlueprint Componentとして実装する。

この作業では、Jiraの **「拾うアクション」** と **「置くアクション」** を扱う。ただし、実際のBPアセットは分けず、**1 Actorにつき1個の `UColoursInteractableComponent` 派生Component**として実装する。

作業対象のBP Component名は **`BPC_PickupPlace`** とする。

## 正本

作業開始前に以下を確認する。内容が食い違う場合は、この指示書ではなく仕様・Jiraを優先する。

- [[050.仕様/050.020.プレイヤー/020.005.インタラクト/インタラクト.040.実装|インタラクト — 実装]]
- [[050.仕様/050.020.プレイヤー/020.010.モノを拾う/モノを拾う.020.仕様|モノを拾う — 仕様]]
- [[050.仕様/050.020.プレイヤー/020.010.モノを拾う/モノを拾う.040.実装|モノを拾う — 実装]]
- [[050.仕様/050.020.プレイヤー/020.020.モノを置く/モノを置く.020.仕様|モノを置く — 仕様]]
- [[050.仕様/050.020.プレイヤー/020.020.モノを置く/モノを置く.040.実装|モノを置く — 実装]]
- [[010.規約/アセット命名規約|アセット命名規約]]
- Jira: 「所持状態管理」「拾うアクション」「置くアクション」「設置・再取得制御」

## 現在の前提

- インタラクト基盤は実装・PIE確認済み。
- Actorがインタラクト候補になれるかは `IColoursInteractable` の有無で決まる。
- `UColoursInteractableComponent` は、インタラクト時の再利用可能な振る舞いを切り出すための基底Component。
- 1 Actorにつき `UColoursInteractableComponent` 派生は **0個または1個**。
- Componentが付いているActorへF入力すると、プレイヤー側から `TryInteract` が呼ばれ、BP派生の `PerformInteraction` へ到達する。
- 所持物の正本はプレイヤー側の「所持状態管理」が持つ。オブジェクト側に別の `HeldActor` 台帳を作らない。

## この作業の範囲

### 今回実装する

1. `BPC_PickupPlace` の作成
2. 「拾うアクション」
3. 「置くアクション」の呼び口と基本処理

### 今回は実装しない

- 保持位置・カメラ方向への追従・角度制限

## 開始条件

### 必須

「所持状態管理」が実装済みで、Blueprintから次の操作ができること。

- 現在の所持Actorを取得できる
- Actorを所持状態へ設定できる
- 現在の所持Actorを解除できる
- 2個同時所持を拒否できる

**上記APIがまだ存在しない場合、その代替として `BPC_PickupPlace` 内に所持状態変数を作らない。**
Componentの作成とイベント骨格までで止め、「所持状態管理」の完成を待つ。

## 作業1: `BPC_PickupPlace` を作る

1. UE5.8.0でDiversion `Colours` の最新 `main` を開く。
2. `Content/Common/Interaction/` に Blueprint Component を作成する。
3. 名前を `BPC_PickupPlace` とする。
4. 親クラスを `UColoursInteractableComponent` にする。
5. このComponentを付けるActor側では `IColoursInteractable` も実装する。
6. 同じActorへ別の `UColoursInteractableComponent` 派生を追加しない。

## 作業2: 拾うアクション

`BPC_PickupPlace` で `PerformInteraction` をOverrideする。

### 処理

1. `Interactor` が有効か確認する。
2. `Interactor` の「所持状態管理」を取得する。
3. 現在の所持Actorが空か確認する。
4. 空なら、`GetOwner()` を所持Actorとして登録する。
5. 登録に成功した場合だけ `PerformInteraction` の戻り値を `true` にする。
6. 所持できなかった場合は `false` を返す。

### ここではしないこと

- Actorを右手へAttachしない。
- Actorの向きをカメラへ追従させない。
- ライト固有処理を呼ばない。
- 別の所持Actorを自動で置く「持ち替え」は実装しない。

### 確認

テストActorに以下を設定する。

- `IColoursInteractable` を実装
- `BPC_PickupPlace` を1個追加
- インタラクト判定に入るCollisionを用意

PIEで確認する。

- 手が空の状態で対象へF入力すると、プレイヤーの所持Actorが対象Actorになる。
- F入力が `PerformInteraction` まで到達する。
- `BPC_PickupPlace` を持たないActorは「拾えるActor」として扱わない。
- 既に所持Actorがある場合に2個同時所持にならない。

ここまで通ればJira「拾うアクション」の確認単位は完了。

## 作業3: 置くアクション

`BPC_PickupPlace` に Blueprint Callable の関数を追加する。

### 関数

`Place(Interactor) -> bool`

- `Interactor`: このActorを現在所持しているプレイヤー
- 戻り値: 置く処理を開始できた場合 `true`

### 処理

1. `Interactor` が有効か確認する。
2. `Interactor` の「所持状態管理」を取得する。
3. 現在の所持Actorが `GetOwner()` と一致するか確認する。
4. 一致しない場合は `false` を返す。
5. 所持状態を解除する。
6. 保持先から `GetOwner()` を **Keep World Transform** でDetachする。
7. 手を離した時点のWorld Rotationを維持する。
8. 対象の物理Bodyに対してSimulate Physicsを有効にし、落下を開始する。
9. 処理を開始できたら `true` を返す。

### 注意

- どの `UPrimitiveComponent` を物理Bodyとして使うかを、`Get Component By Class` の「最初に見つかったもの」に依存させない。
- 対象Actor側から、物理挙動を担当するComponentが明示できる構造にする。
- その指定方法がまだプロジェクト内で決まっていない場合は、独自ルールを確定せずMoriへ確認する。
- プレイヤーの「置く」キー割り当ては現時点で未確定。今回のComponentでは `Place` を外から呼べるところまで作り、恒久的な入力割り当てを勝手に追加しない。
- PIE確認のため一時的な呼出経路を作った場合は、恒久仕様でないものをcommitへ残さない。

### 確認

テストActorを所持状態にして `Place` を呼び、以下を確認する。

- プレイヤーの所持Actorが空になる。
- 対象Actorが保持先から外れる。
- 手を離す直前のWorld Rotationを維持する。
- Physicsが有効になり落下を開始する。

ここまで通ればJira「置くアクション」の確認単位は完了。

## 次Task: 設置・再取得制御

「置くアクション」が完了した後、同じ `BPC_PickupPlace` を拡張する。

対象は以下。

- 落下中は再インタラクト不可
- 上向き面への接地を検出
- 設置許容角度内なら固定
- 急斜面なら回転せず滑る
- 接地後は滑っていても再インタラクト可能

この部分はJira「設置・再取得制御」として別に検証する。

## 変更してはいけない範囲

この作業のためだけに、以下を変更しない。

- `UColoursInteractionComponent` の候補検出・選択ロジック
- Fキーの既存インタラクト入力
- `IColoursInteractable` の責務
- `UColoursInteractableComponent` のC++共通フロー
- 保持・追従システム
- 携帯ライトのライト処理
- 壁・色システム

既存基盤の変更が必要だと判断した場合は、先にMoriへ理由を共有する。

## 作業完了時

1. 各Taskの確認項目をPIEで実施する。
2. 実際に確認できた項目だけJiraへ記録する。
3. 対象Jira Taskのステータスを更新する。
4. Diversion `main` へ作業をcommitする。
5. 作ったBPアセット名と配置場所、PIE確認結果を引き継ぎコメントへ残す。

## 未決事項

以下はこの指示書では決めない。

- 「置く」を呼ぶ恒久的な入力キー
- 汎用Actorが物理Bodyを明示する具体的なBP上の方法
- 持ち替えの実装時期

これらは推測で確定せず、必要になった時点で確認する。
