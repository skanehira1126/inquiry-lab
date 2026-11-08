import xml.etree.ElementTree as ET
from itertools import pairwise

import matplotlib as mpl
import numpy as np
import polars as pl
import pytest
from matplotlib import image, pyplot
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from inquiry_lab.visualize.common import plot_count, plot_histogram, plot_scatter


@pytest.mark.parametrize("hue", [None, "group"])
def test_histogram_preserves_counts_with_common_bins(tmp_path, monkeypatch, hue):
    df = pl.DataFrame(
        {"measurement": [20.0, -20.0, -20.0, 0.0, -20.0], "group": ["b", "a", "a", "b", "a"]}
    )
    original = df.clone()
    hist = Axes.hist
    observed = []

    def capture(self, *args, **kwargs):
        result = hist(self, *args, **kwargs)
        observed.append(result[:2])
        return result

    monkeypatch.setattr(Axes, "hist", capture)
    output = tmp_path / "artifacts" / "hist.svg"
    assert plot_histogram(df, column="measurement", hue=hue, output=output) == output
    assert df.equals(original)
    expected = np.array([[3, 0, 0, 0], [0, 0, 1, 1]])
    if hue is None:
        expected = expected.sum(axis=0)
    for counts, edges in observed:
        np.testing.assert_array_equal(counts, expected)
        np.testing.assert_allclose(edges, [-20, -10, 0, 10, 20])
    assert observed
    svg = output.read_text()
    ET.parse(output)
    assert "Count" in svg
    assert "measurement" in svg
    assert "Score distribution" not in svg
    if hue is None:
        assert "All (n = 5)" in svg
    else:
        assert "a (n = 3)" in svg
        assert "b (n = 2)" in svg
        assert svg.index("a (n = 3)") < svg.index("b (n = 2)")


def test_histogram_accepts_constant_values_and_numeric_hue(tmp_path):
    df = pl.DataFrame({"value": [-5.0, -5.0], "group": [1, 0]})
    output = tmp_path / "constant.svg"
    plot_histogram(df, column="value", hue="group", output=output)
    svg = output.read_text()
    assert "0 (n = 1)" in svg
    assert "1 (n = 1)" in svg


def test_histogram_box_summary_shares_axis_and_group_colors(tmp_path, monkeypatch):
    df = pl.DataFrame({"value": [0, 1, 2, 3, 100, 10, 10], "group": ["a"] * 5 + ["b"] * 2})
    savefig = Figure.savefig
    figures = []

    def capture(self, *args, **kwargs):
        figures.append(self)
        return savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    plot_histogram(df, column="value", hue="group", output=tmp_path / "box.svg")
    box_ax, hist_ax = figures[0].axes
    assert box_ax.get_shared_x_axes().joined(box_ax, hist_ax)
    assert box_ax.get_xlim() == hist_ax.get_xlim()
    assert [tick.get_text() for tick in box_ax.get_yticklabels()] == ["a (n = 5)", "b (n = 2)"]
    first_box, second_box = box_ax.patches
    np.testing.assert_allclose(first_box.get_path().vertices[:, 0], [1, 1, 3, 3, 1, 1])
    np.testing.assert_allclose(second_box.get_path().vertices[:, 0], 10)
    # Lines are the two whiskers, two caps, median and fliers for each box.
    np.testing.assert_allclose(box_ax.lines[4].get_xdata(), [2, 2])
    np.testing.assert_allclose(box_ax.lines[5].get_xdata(), [100])
    hist_by_label = {patch.get_label(): patch for patch in hist_ax.patches}
    np.testing.assert_allclose(
        first_box.get_facecolor(), hist_by_label["a (n = 5)"].get_facecolor()
    )
    np.testing.assert_allclose(
        second_box.get_facecolor(), hist_by_label["b (n = 2)"].get_facecolor()
    )


@pytest.mark.parametrize("hue", [None, "group"])
def test_scatter_preserves_pairs_and_group_counts(tmp_path, monkeypatch, hue):
    df = pl.DataFrame(
        {"x": [3, -1, 3, 0], "y": [2, 9, 2, 7], "group": [1, 0, 1, 0], "unused": [None] * 4}
    )
    original = df.clone()
    savefig = Figure.savefig
    figures = []

    def capture(self, *args, **kwargs):
        figures.append(self)
        return savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    output = tmp_path / "artifacts" / "scatter.svg"
    assert plot_scatter(df, x="x", y="y", hue=hue, output=output) == output
    assert df.equals(original)
    ET.parse(output)
    ax = figures[0].axes[0]
    expected = [[[-1, 9], [0, 7]], [[3, 2], [3, 2]]]
    names = ["0 (n = 2)", "1 (n = 2)"]
    if hue is None:
        expected = [[[3, 2], [-1, 9], [3, 2], [0, 7]]]
        names = ["All (n = 4)"]
    assert len(ax.collections) == len(expected)
    for index, (points, pairs) in enumerate(zip(ax.collections, expected, strict=True)):
        np.testing.assert_allclose(points.get_offsets(), pairs)
        np.testing.assert_allclose(
            points.get_facecolors()[0, :3], mpl.colormaps["tab10"](index)[:3]
        )
    assert [label.get_text() for label in ax.get_legend().get_texts()] == names
    assert ax.get_xlabel() == "x"
    assert ax.get_ylabel() == "y"
    bounds = ax.get_window_extent()
    assert bounds.width == pytest.approx(bounds.height)


@pytest.mark.parametrize(
    "df",
    [
        pl.DataFrame({"value": [], "group": []}),
        pl.DataFrame({"group": [0, 1]}),
        pl.DataFrame({"value": [0.1, 0.9]}),
        pl.DataFrame({"value": [0.1, None], "group": [0, 1]}),
        pl.DataFrame({"value": [0.1, float("nan")], "group": [0, 1]}),
        pl.DataFrame({"value": [0.1, float("inf")], "group": [0, 1]}),
        pl.DataFrame({"value": ["low", "high"], "group": [0, 1]}),
        pl.DataFrame({"value": [0.1, 0.9], "group": [0, None]}),
        pl.DataFrame({"value": [0.1, 0.9], "group": [0.0, float("nan")]}),
        pl.DataFrame({"value": [0.1, 0.9], "group": [[0], [1]]}),
        pl.DataFrame({"value": range(21), "group": range(21)}),
    ],
)
def test_histogram_rejects_invalid_numeric_and_hue_inputs_before_creating_output(tmp_path, df):
    # Histogram owns the full numeric/hue input matrix shared with scatter.
    output = tmp_path / "artifacts" / "hist.png"
    with pytest.raises(ValueError):
        plot_histogram(df, column="value", hue="group", output=output)
    assert not output.parent.exists()


@pytest.mark.parametrize("axis", ["x", "y"])
def test_scatter_validates_both_axes_before_overwriting(tmp_path, axis):
    data = {"x": [0, 1], "y": [2, 3]}
    data[axis] = [None, 1]
    output = tmp_path / "scatter.png"
    output.write_bytes(b"keep")
    with pytest.raises(ValueError):
        plot_scatter(pl.DataFrame(data), x="x", y="y", output=output)
    assert output.read_bytes() == b"keep"


def test_scatter_rejects_too_many_groups_before_creating_output(tmp_path):
    output = tmp_path / "artifacts" / "scatter.png"
    df = pl.DataFrame({"x": range(21), "y": range(21), "group": range(21)})
    with pytest.raises(ValueError, match="at most 20 groups"):
        plot_scatter(df, x="x", y="y", hue="group", output=output)
    assert not output.parent.exists()


@pytest.mark.parametrize("plot", [plot_histogram, plot_scatter, plot_count])
def test_png_style_is_fixed_without_changing_caller_settings_or_open_figures(
    tmp_path, monkeypatch, plot
):
    df = pl.DataFrame({"group": [0, 0, 1, 1], "value": [0.1, 0.4, 0.35, 0.8]})
    columns = {"x": "value", "y": "group"} if plot is plot_scatter else {"column": "value"}
    default_output = tmp_path / "default.png"
    output = tmp_path / "custom.png"
    output.write_bytes(b"old output")
    figures_before = pyplot.get_fignums()
    plot(df, **columns, hue="group", output=default_output)
    monkeypatch.setitem(mpl.rcParams, "backend", "svg")
    with mpl.rc_context(
        {"axes.facecolor": "black", "font.size": 30, "text.usetex": True, "savefig.dpi": 20}
    ):
        assert plot(df, **columns, hue="group", output=str(output)) == output
        assert mpl.rcParams["axes.facecolor"] == "black"
        assert mpl.rcParams["text.usetex"] is True
        assert mpl.rcParams["backend"] == "svg"
    assert pyplot.get_fignums() == figures_before
    assert output.read_bytes() == default_output.read_bytes()
    pixels = image.imread(output)
    assert pixels.shape[:2] == (900, 900)
    assert pixels[:, :, :3].min() < 0.5


@pytest.mark.parametrize("plot", [plot_histogram, plot_scatter, plot_count])
def test_unsupported_format_does_not_overwrite_output(tmp_path, plot):
    output = tmp_path / "hist.txt"
    output.write_text("keep")
    columns = {"x": "value", "y": "label"} if plot is plot_scatter else {"column": "value"}
    with pytest.raises(ValueError, match="extension"):
        plot(pl.DataFrame({"label": [0, 1], "value": [0.2, 0.8]}), **columns, output=output)
    assert output.read_text() == "keep"


@pytest.mark.parametrize("plot", [plot_histogram, plot_scatter])
def test_pdf_supports_twenty_single_point_groups(tmp_path, monkeypatch, plot):
    df = pl.DataFrame({"value": range(20), "group": range(20)})
    columns = {"column": "value"} if plot is plot_histogram else {"x": "value", "y": "value"}
    output = tmp_path / "groups.pdf"
    savefig = Figure.savefig
    figures = []

    def capture(self, *args, **kwargs):
        figures.append(self)
        return savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    plot(df, **columns, hue="group", output=output)
    assert output.read_bytes().startswith(b"%PDF-")
    figure = figures[0]
    figure.canvas.draw()
    plot_ax = figure.axes[-1]
    legend = plot_ax.get_legend()
    bounds = legend.get_window_extent()
    plot_bounds = plot_ax.get_window_extent()
    assert bounds.x0 >= plot_bounds.x0 and bounds.y0 >= plot_bounds.y0
    assert bounds.x1 <= plot_bounds.x1 and bounds.y1 <= plot_bounds.y1
    if plot is plot_histogram:
        labels = [tick.get_window_extent() for tick in figure.axes[0].get_yticklabels()]
        assert all(upper.y0 >= lower.y1 for upper, lower in pairwise(labels))


@pytest.mark.parametrize("aggregated", [False, True])
@pytest.mark.parametrize("normalize", [False, True])
@pytest.mark.parametrize("hue", [None, "origin"])
def test_count_aligns_categories_and_matches_aggregated_counts(
    tmp_path, monkeypatch, aggregated, normalize, hue
):
    if aggregated:
        df = pl.DataFrame(
            {
                "total": ["b", "a", "a", "c", "a"],
                "origin": ["dev", "dev", "dev", "test", "test"],
                "category": [1, 1, 2, 1, 1],
            }
        )
    else:
        df = pl.DataFrame(
            {"total": ["b", "a", "a", "a", "c", "a"], "origin": ["dev"] * 4 + ["test"] * 2}
        )
    original = df.clone()
    savefig = Figure.savefig
    figures = []

    def capture(self, *args, **kwargs):
        figures.append(self)
        return savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    output = tmp_path / "artifacts" / "count.svg"
    assert (
        plot_count(
            df,
            column="total",
            hue=hue,
            count="category" if aggregated else None,
            normalize=normalize,
            output=output,
        )
        == output
    )
    assert df.equals(original)
    ET.parse(output)
    ax = figures[0].axes[0]
    expected = np.array([[3, 1, 0], [1, 0, 1]], dtype=float)
    names = ["dev (n = 4)", "test (n = 2)"]
    if hue is None:
        expected = np.array([[4, 1, 1]], dtype=float)
        names = ["All (n = 6)"]
    if normalize:
        expected /= expected.sum(axis=1, keepdims=True)
    np.testing.assert_allclose(
        [[bar.get_width() for bar in container] for container in ax.containers], expected
    )
    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["a", "b", "c"]
    assert [text.get_text() for text in ax.get_legend().get_texts()] == names
    assert ax.get_xlabel() == ("Share within each group" if normalize else "Count")
    if hue is not None:
        assert ax.containers[0][0].get_y() != ax.containers[1][0].get_y()


@pytest.mark.parametrize(
    "df",
    [
        pl.DataFrame({"category": []}),
        pl.DataFrame({"other": ["a"]}),
        pl.DataFrame({"category": ["a", None]}),
        pl.DataFrame({"category": [["a"], ["b"]]}),
        pl.DataFrame({"category": [0.0, float("inf")]}),
        pl.DataFrame({"category": range(21)}),
    ],
)
def test_count_rejects_invalid_categories_before_creating_output(tmp_path, df):
    output = tmp_path / "artifacts" / "count.png"
    with pytest.raises(ValueError):
        plot_count(df, column="category", output=output)
    assert not output.parent.exists()


@pytest.mark.parametrize("weights", [[-1, 2], [1, None], [1.5, 2.0], [True, False]])
def test_count_rejects_invalid_supplied_counts_without_overwriting(tmp_path, weights):
    output = tmp_path / "count.png"
    output.write_bytes(b"keep")
    df = pl.DataFrame({"category": ["a", "b"], "n": weights})
    with pytest.raises(ValueError, match="non-negative integers"):
        plot_count(df, column="category", count="n", output=output)
    assert output.read_bytes() == b"keep"


def test_count_requires_existing_count_and_hue_columns(tmp_path):
    df = pl.DataFrame({"category": ["a"]})
    output = tmp_path / "artifacts" / "count.png"
    for option in ["count", "hue"]:
        with pytest.raises(ValueError, match="existing column"):
            plot_count(df, column="category", **{option: "missing"}, output=output)
    assert not output.parent.exists()


def test_count_preserves_zero_counts_but_rejects_undefined_group_proportions(tmp_path):
    df = pl.DataFrame({"category": ["a", "b"], "origin": ["dev", "test"], "n": [0, 3]})
    output = tmp_path / "count.pdf"
    plot_count(df, column="category", hue="origin", count="n", output=output)
    assert output.read_bytes().startswith(b"%PDF-")
    normalized = tmp_path / "artifacts" / "proportions.png"
    with pytest.raises(ValueError, match="positive total"):
        plot_count(
            df, column="category", hue="origin", count="n", normalize=True, output=normalized
        )
    assert not normalized.parent.exists()
