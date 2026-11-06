---
name: inquiry-lab-api
description: "inquiry-labのPython APIを使うコードの実装・修正や、利用できる関数の確認に使う。用途に合う公開関数を選び、入力条件・呼び出し方・保存方法を確認する。分析全体の設計・進行はanalyze、分析方法の判断は各専門Skillが扱う。"
---

# inquiry-labのAPIを使う

分析で選んだ方法を、inquiry-labの公開関数で実装できるか確認する。
入力は行いたい処理、対象のDataFrameと列の意味、保存先、利用環境。
関数の確認だけなら適用可否と呼び出し例を返し、実装依頼なら既存の分析コードへ組み込む。
分析計画だけの段階では下の用途表で提供範囲を確認し、実装時に必要な参照だけを読む。

## 用途から選ぶ

| 行いたい処理 | 公開関数 | 実装時に読む参照 |
|---|---|---|
| 数値列の分布、カテゴリ別の分布を描く | `visualize.common.plot_histogram` | [ヒストグラム](references/histogram.md) |
| 2値分類の識別性能をROC・AUCで示す | `visualize.ml.classifier.plot_roc_curve` | [分類モデルのグラフ](references/classifier.md) |
| 予測確率と実際の陽性率の対応を示す | `visualize.ml.classifier.plot_calibration_curve` | [分類モデルのグラフ](references/classifier.md) |

表のモジュール名には `inquiry_lab.` を付けてimportする。
描画に使う評価対象、分割、除外規則は呼出元の分析計画に従う。
APIに合わせて評価データや分析方法を変更しない。要件を満たす関数がなければ不足を示し、
案件で使える別のライブラリや実装を選ぶ。未提供の関数や引数を推測で呼び出さない。

## 呼び出す前に確認する

- 実行環境にPythonパッケージと `visualize` extraがあることを確認する。
  プラグインの導入だけではPython依存は入らない。導入方法は[README](../../README.md#pythonからグラフを保存する)を参照する。
- 入力はPolars DataFrame。列名だけでなく値の意味と参照先の条件を照合する。
  指定列の欠損・非有限値は暗黙に除外されない。前処理が必要なら分析側で対象と理由を決める。
- 保存先を `output` で渡す。対応形式はPNG（900×900 px）・SVG・PDFで、親ディレクトリは自動作成し、
  同名ファイルは上書きする。runがある場合はその `artifacts/` に保存する。
  戻り値は保存先の `Path`。入力は変更せず、Figure・Axesや見た目の調整引数は公開しない。

利用環境と説明に差がある場合は、実行に使う環境のパッケージ版・公開関数のsignature・docstringを確認する。
実装した場合は依頼された範囲で実行し、保存した図の軸・凡例・件数などが入力と意図に合うか確認する。
未実行ならその旨を示す。APIの利用確認だけを理由に新しい分析runや統合レポートを作らない。
