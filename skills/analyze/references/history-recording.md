# 履歴JSONの記録手順

分析の保存先を作成・再開し、試行または判断を記録するときに読む。
項目の書き方と本文に載せる根拠の選び方は [成果物の共通方針](deliverables.md) に従う。

## 保存先と記録単位

- 依頼と合意した条件は `requests/001-initial.md` に残す。変更の経緯は判断の記録から辿れるようにする。
- 実行前の仮説・計画は、そのrunの `runs/<番号>/result.md` などへ残す。実行後に結果と判断をJSONへまとめる。
  既存のresult.mdは詳細な実行資料として参照できる。生成する履歴詳細と同じ内容を二重に保守する必要はない。
- 履歴の正本は `history/NNNNNN.json`。`作業履歴.md` と `history/NNNNNN.md` は生成物なので、訂正はJSONへ反映して再生成する。
- 全体目標・終了条件と現在の個別作業は[全体状態の手順](state.md)で`state.json`へ保存する。
  `current_state`は履歴の各時点の短い現在地として残し、stateには反映済みの履歴番号を記す。
- 画像・CSV・設定・実行コードはrunの成果物フォルダや既存の保存先へ置き、JSONから参照する。
  `output.md` はテーマ別の雛形を用いてエージェントが執筆する。CLIは最終レポートを生成しない。

既存の番号を確認し、`sequence` は全記録を通じた作業順の1〜999999の整数を選ぶ。
runのラベル `run_id` と履歴の `sequence` は別物で、判断の記録もsequenceを使う。
`run new` が採番するのはrunだけで、履歴のsequenceは採番しない。
並行作業では担当間でsequenceを割り当て、番号が衝突したら既存記録を確認する。

## JSONの項目

| 対象 | 必須項目 |
|---|---|
| 全記録 | `sequence`、`kind`、`current_state`、`references` |
| `kind: "run"` | `run_id`、`hypothesis`、`verification`、`results`、`discussion` |
| `kind: "decision"` | `decision`、`reason` |

仮説から考察までの4項目と、判断・理由は、1件以上の文字列を持つ配列。
文字列は前後に空白を付けない空でない1行とし、箇条書き1項目に対応させる。
実行失敗でも、結果に失敗内容・未測定の範囲、考察に次の判断を記し、未実施の結果を補わない。

`current_state` は現在の判断、停止理由または次の作業を示す1行。
`references` は `{"label": "何を確認するか", "target": "参照先"}` の配列で、参照がなければ `[]`。
ローカルのtargetは**ワークスペース基準**の相対パス、外部の原本は対象URLとする。
生成時に詳細文書の位置に合わせてリンクが調整される。

任意項目は次のとおり。新規記録には読みやすい `title` と `summary` を付ける。

- `title`：短い題を表す1行。
- `summary`：分かったことと判断を1〜2文で記した1行。省略した既存記録ではcurrent_stateを表示する。
- `depends_on`：前提に使った記録のsequenceの配列。記録済みで、自分より小さい番号に限り、重複させない。
- `base_run`：runだけに指定できる。出発点にした過去のrun記録のsequence。run_idではない。

未知のキーは追加しない。パラメータなどは検証欄か参照先に残す。

## 記録して表示する

次は実行前の計画を残した後、比較を試みたがデータを取得できなかった場合の記録例。

```json
{
  "sequence": 1,
  "kind": "run",
  "run_id": "run-001",
  "title": "基準設定の評価を試行",
  "summary": "入力データを取得できず、基準性能は未測定。取得先の確認後に再開する。",
  "hypothesis": ["候補と比較するため、基準設定の性能を把握する。"],
  "verification": ["依頼で指定された入力の取得を試みた。取得に失敗し、学習は実行していない。"],
  "results": ["入力を取得できなかった。性能値は未測定。"],
  "discussion": ["設定の良否は判断できない。取得先を確認してから評価を再開する。"],
  "current_state": "入力の取得先を確認するまで評価を中断。",
  "references": [{"label": "依頼と入力の指定", "target": "requests/001-initial.md"}]
}
```

作成した1件分のJSONを入力に渡す。入力ファイルは取り込み後の正本ではない。

```bash
inquiry-lab history record --workspace <分析先> --input <入力JSON>
inquiry-lab history render --workspace <分析先>
```

`record` は同番号の記録を上書きしない。`render` は全JSONを一度に読み、短い履歴と各記録の詳細を生成する。
記録済みJSONがなければrenderは実行しない。生成物の要約・現在地と、詳細から根拠への参照を確認する。
Mermaidの描画はMarkdownエディタ・ビューアに任せる。
