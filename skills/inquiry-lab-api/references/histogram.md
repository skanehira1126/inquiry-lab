# 数値列の分布

`inquiry_lab.visualize.common.plot_histogram(df, *, output, column, hue=None)` を使う。
数値列を `column` で指定し、`hue` を省略すると全体、列名を渡すと値ごとに色分けする。
分類スコアだけでなく一般の計測値・集計値にも使える。分類スコアなら `column="score"` とする。

```python
import polars as pl

from inquiry_lab.visualize.common import plot_histogram

observations = pl.DataFrame({"value": [-2, 3, 8, 12], "group": ["a", "a", "b", "b"]})
plot_histogram(observations, column="value", output="runs/001/artifacts/distribution.png")
plot_histogram(observations, column="value", hue="group", output="runs/001/artifacts/by-group.png")
```

- 空のDataFrame、対象列の非数値・null・NaN・無限値はエラーにする。
  指定していない列の欠損は無視する。
- `hue` はソート可能なスカラー値の列で、数値でもカテゴリとして扱う。最大20群で、値順に配色する。
  `hue` のnull・NaN・無限値も拒否する。
- 対象列全体からNumPyの `auto`（スタージェス則とFreedman–Diaconis則）で等幅ビンを決め、
  全群で境界を共有する。別々の呼び出し間でビンを固定する引数はない。
- 縦軸は件数。群を重ねて表示し、積み上げや正規化は行わない。凡例に群別件数を添える。
  群の大きさが違う場合は、棒の高さだけを分布形状の差と解釈しない。

実装：[common.py](../../../src/inquiry_lab/visualize/common.py)。
