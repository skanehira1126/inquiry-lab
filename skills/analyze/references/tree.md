# 作業者の現在地と共有 tree

全体進行担当は、目的を Core に置き、調べる仮説を tree に登録する。担当を委任するときは、
共有 tree の絶対パス、担当仮説 ID、依頼と割当 run を渡す。

```bash
inquiry-lab tree init tree.json --core-id C --goal '店舗の需要予測が外れる条件を調べる'
inquiry-lab tree add-hypothesis tree.json H1 --core --hypothesis '冬は誤差が大きい' --constraint '同じ店舗群で比較する'
```

## 委任の単位

- **調査を分担する。** 仮説の担当者が、同じ仮説の下で並行して進める調査を分け、各作業者の依頼に調査 ID と割当 run を記す。作業者は自分の調査の `status`・`result`・`references` を更新して run を返す。仮説の担当者が各結果を照合し、仮説の `result` と `status` を更新する。
- **仮説ごと任せる。** 一つの仮説を一人に渡し、直下の調査から仮説の結論・状態の更新まで任せる。独立した仮説は別々の作業者に並行して任せられる。

単独で進める場合は、自分で調査と仮説の両方を更新する。

## 着手と再開

作業者は着手時に自分の保存先を決め、`state start` で担当を記録する。並行する作業者には別々のパスを使う。
以下は分析先から実行する例。再開や引き継ぎに使えるよう、コマンドが返す state の絶対パスを依頼や作業記録に残す。

```bash
inquiry-lab state start agents/A/state.json --tree tree.json --hypothesis H1
inquiry-lab state show agents/A/state.json
```

state の中身は共有 tree の参照先と担当仮説 ID の2項目。調査を分担する作業者も同じ仮説 ID を使い、自分の調査 ID は依頼で確認する。

```json
{
  "tree_path": "../../tree.json",
  "hypothesis_id": "H1"
}
```

`start` は指定した tree に仮説が存在することを検証し、親ディレクトリと新しい state を作る。
既存の保存先を指定するとエラーになる。保存時の相対参照は state ファイルの親ディレクトリを基準とする。
再開時や compaction 後、現在地が必要になったら `state show STATE` を実行する。全体進行担当は
`tree details TREE CORE_ID` で全体状態を、`tree search TREE --type hypothesis` で各仮説の状態を確認できる。
検索は `Pruned` の仮説とその子孫を除く。見送った枝を再検討するときは `--include-pruned-branch` を付ける。

`show` は最新の tree を読み、tree の絶対パス、Core の ID と目的、担当仮説の全項目、直下の全調査を JSON で返す。
調査の問い・状態・結果・参照先は全文を表示する。調査がなければ空配列、未回答の結果は `null`。
仮説 ID が分かっているときは `tree status TREE ID` からも同じ内容を取得できる。
担当を再開するときは `tree ancestors TREE HYPOTHESIS_ID --json` で親仮説の状態・制約と Core の状態を照合し、次の調査に進むか判断する。

## 調査を進める

調査の停止理由は該当する調査の結果に記し、仮説全体を保留するかは仮説の担当者が判断する。
実行 ID・ログ・成果物を run に残し、調査の `references` に参照先を記す。実行中の調査は原本で稼働や出力を確認する。

```bash
inquiry-lab tree update tree.json hypothesis H1 --status Active
inquiry-lab tree add-research tree.json R1 --parent H1 --question '冬と春の誤差はどう違うか'
inquiry-lab tree update tree.json research R1 --status Blocked --result '春の実績は到着待ち' --add-reference winter runs/001/result.md
```

## 担当の切り替えと終了

同じ作業者が別の枝を引き受けたら、同じ tree 内の既存の仮説を指定して担当を切り替える。
指定に失敗した場合は元の担当が残る。作業を中断するときは state を残す。
作業を終えたら結果と参照先を tree・run に記録してから、自分の state を削除する。

```bash
inquiry-lab tree add-hypothesis tree.json H2 --core --hypothesis '欠品の翌日は誤差が大きい'
inquiry-lab state update agents/A/state.json --hypothesis H2
inquiry-lab state finish agents/A/state.json
```

`finish` が削除するのは指定した作業者の state ファイルだけ。全体進行担当は各枝の結論と根拠を照合して、Core の知見と全体状態を更新する。
