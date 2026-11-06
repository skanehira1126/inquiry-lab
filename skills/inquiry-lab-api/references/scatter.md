# 数値列どうしの関係

`inquiry_lab.visualize.common.plot_scatter(df, *, output, x, y, hue=None)` を使う。
横軸・縦軸の数値列を `x`・`y` で指定し、`hue` を渡すとカテゴリごとに色分けする。

```python
import polars as pl

from inquiry_lab.visualize.common import plot_scatter

observations = pl.DataFrame(
    {"size": [1, 2, 3, 4], "duration": [2, 5, 4, 8], "group": ["a", "a", "b", "b"]}
)
plot_scatter(
    observations, x="size", y="duration", hue="group", output="runs/001/artifacts/scatter.png"
)
```

- 1行を1点として、同じ行の `x` と `y` を組み合わせる。全行を描画し、間引き・集約・ジッター・
  回帰線の追加は行わない。点の重なりは半透明で示すが、重複点の個数を正確には読み取れない。
- 空のDataFrame、存在しない列、両軸の非数値・null・NaN・無限値はエラーにする。
  指定していない列の欠損は無視する。
- `hue` はソート可能なスカラー値の列で、数値でもカテゴリとして扱う。最大20群で、値順に配色する。
  `hue` のnull・NaN・無限値も拒否する。凡例に群別件数を添える。
- 軸は線形で、列名をラベルにする。対象の選択・変換・集約が必要なら、分析側で理由と件数を記録して行う。
  関係の見え方だけで因果関係とは判断しない。
- 軸で囲まれた描画領域の縦横比は1:1に固定する。両軸の数値範囲はそれぞれのデータに合わせる。
- 凡例は描画領域内で、Matplotlibの `loc="best"` により重なりが少ない位置を自動選択する。
  多群の場合は複数列に分ける。重なりを完全になくす保証はない。

実装：[common.py](../../../src/inquiry_lab/visualize/common.py)。
