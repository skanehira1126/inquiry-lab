import xml.etree.ElementTree as ET

import matplotlib as mpl
import numpy as np
import polars as pl
import pytest
from matplotlib import image, pyplot
from matplotlib.axes import Axes

from inquiry_lab.visualize.common import plot_histogram


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
def test_invalid_histogram_input_does_not_create_output(tmp_path, df):
    output = tmp_path / "artifacts" / "hist.png"
    with pytest.raises(ValueError):
        plot_histogram(df, column="value", hue="group", output=output)
    assert not output.parent.exists()


def test_png_style_is_fixed_without_changing_caller_settings_or_open_figures(
    tmp_path, monkeypatch
):
    df = pl.DataFrame({"group": [0, 0, 1, 1], "value": [0.1, 0.4, 0.35, 0.8]})
    default_output = tmp_path / "default.png"
    output = tmp_path / "custom.png"
    output.write_bytes(b"old output")
    figures_before = pyplot.get_fignums()
    plot_histogram(df, column="value", hue="group", output=default_output)
    monkeypatch.setitem(mpl.rcParams, "backend", "svg")
    with mpl.rc_context(
        {"axes.facecolor": "black", "font.size": 30, "text.usetex": True, "savefig.dpi": 20}
    ):
        assert plot_histogram(df, column="value", hue="group", output=str(output)) == output
        assert mpl.rcParams["axes.facecolor"] == "black"
        assert mpl.rcParams["text.usetex"] is True
        assert mpl.rcParams["backend"] == "svg"
    assert pyplot.get_fignums() == figures_before
    assert output.read_bytes() == default_output.read_bytes()
    pixels = image.imread(output)
    assert pixels.shape[:2] == (900, 900)
    assert pixels[:, :, :3].min() < 0.5


def test_unsupported_format_does_not_overwrite_output(tmp_path):
    output = tmp_path / "hist.txt"
    output.write_text("keep")
    with pytest.raises(ValueError, match="extension"):
        plot_histogram(
            pl.DataFrame({"label": [0, 1], "value": [0.2, 0.8]}), column="value", output=output
        )
    assert output.read_text() == "keep"
