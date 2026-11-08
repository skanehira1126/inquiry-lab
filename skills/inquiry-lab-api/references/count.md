# カテゴリ別の件数・割合

`inquiry_lab.visualize.common.plot_count` を使う。

```python
plot_count(df, *, output, column, hue=None, count=None, normalize=False)
```

`column` のカテゴリを数えて横向きの棒グラフにする。`hue` を指定すると群ごとに色分けして並べる。
未集計データは各行を1件として数える。集計済みデータは `count` に件数列を指定し、同じカテゴリ・群の件数を合計する。
列名などから集計済みかどうかを自動判定しない。

```python
import polars as pl

from inquiry_lab.visualize.common import plot_count

rows = pl.DataFrame({"kind": ["a", "a", "b"], "origin": ["dev", "dev", "holdout"]})
plot_count(rows, column="kind", hue="origin", output="runs/001/artifacts/count.png")

counts = pl.DataFrame({"kind": ["a", "b"], "origin": ["dev", "holdout"], "n": [2, 1]})
plot_count(
    counts,
    column="kind",
    hue="origin",
    count="n",
    normalize=True,
    output="runs/001/artifacts/proportions.png",
)
```

- `normalize=False` は件数、`True` は各群の合計件数を分母とする割合。`hue` がなければ全体を分母にする。
- カテゴリ・群は値順で、それぞれ最大20。数値もカテゴリとして扱う。存在しない組み合わせは0とし、全カテゴリを省略せず表示する。
- 空入力、指定列の欠損・非有限値、ネスト・object型のカテゴリを拒否する。必要な欠損処理は呼出元で決める。
- `count` は欠損のない非負整数列。0件のカテゴリも残す。割合表示で合計0件の群がある場合はエラーにする。
- 凡例には群別の合計件数を示す。集計済みデータでも、入力行数ではなく元の観測件数になる。
- PNG（900×900 px）・SVG・PDFに保存し、親ディレクトリを作成、同名ファイルを上書きして`Path`を返す。
  入力や呼出元の描画設定は変更しない。

実装：[common.py](../../../src/inquiry_lab/visualize/common.py)。
