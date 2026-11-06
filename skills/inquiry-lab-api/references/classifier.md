# 2値分類のROCと較正

`inquiry_lab.visualize.ml.classifier` の次の関数を使う。

```python
plot_roc_curve(df, *, output, label="label", score="score", pos_label=1)
plot_calibration_curve(df, *, output, label="label", score="score", pos_label=1)
```

## 共通の入力

正解列を `label`、陽性クラスに対するスコア列を `score` で指定する。
正解は必ず2クラスを含み、陽性ラベルは既定で `1`。別のラベルなら `pos_label="yes"` などを渡す。
`predict_proba` から作る場合は、モデルのクラス順を確認し、陽性クラスの列を使う。
両関数とも、空の入力、指定列の欠損・非有限値、非数値スコア、単一クラス・多クラスを拒否する。
指定した2列だけを使い、暗黙の除外や補完は行わない。

```python
import polars as pl

from inquiry_lab.visualize.ml.classifier import plot_calibration_curve, plot_roc_curve

predictions = pl.DataFrame(
    {"actual": ["no", "no", "yes", "yes"], "probability": [0.1, 0.4, 0.35, 0.8]}
)
plot_roc_curve(
    predictions,
    label="actual",
    score="probability",
    pos_label="yes",
    output="runs/001/artifacts/roc.png",
)
plot_calibration_curve(
    predictions,
    label="actual",
    score="probability",
    pos_label="yes",
    output="runs/001/artifacts/calibration.png",
)
```

## ROC曲線

`plot_roc_curve` はROC曲線、AUC、対角の基準線を保存する。
スコアは大きいほど陽性とし、陽性確率または決定スコアを渡す。0〜1の範囲には限定しない。
AUCは図中に表示し、数値を返すAPIではない。レポートや候補比較に数値が必要なら、同じ対象・陽性定義で別途算出する。

## 較正曲線

`plot_calibration_curve` のスコアには0〜1の予測確率が必要で、範囲外の決定スコアは拒否する。
ROCに使えるスコアでも、確率でなければ較正には使わない。

0〜1を10等分し、各ビンの平均予測確率と実際の陽性率を線と点で表示する。
同じビンのサンプル数を背景の棒とラベルで重ね、右軸に件数を表示する。
対角線は予測確率と陽性率が一致する基準。ビン境界上の値は左側のビンに含め、0は最初、1は最後に含める。
空のビンは点を描かず線を切り、陽性率0とは扱わない。ビン数・境界の変更引数はない。

実装：[classifier.py](../../../src/inquiry_lab/visualize/ml/classifier.py)。
