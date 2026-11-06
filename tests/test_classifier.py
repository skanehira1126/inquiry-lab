import xml.etree.ElementTree as ET

import matplotlib as mpl
import numpy as np
import polars as pl
import pytest
from matplotlib import image, pyplot
from matplotlib.axes import Axes

from inquiry_lab.visualize.ml.classifier import plot_roc_curve, plot_score_histogram


@pytest.mark.parametrize(
    ("labels", "scores", "positive", "expected"),
    [
        ([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8], 1, "0.750"),
        ([0, 1], [0.5, 0.5], 1, "0.500"),
        ([0, 1], [1.0, -1.0], 1, "0.000"),
        (["yes", "no"], [2.0, -2.0], "yes", "1.000"),
        ([0, 1], [0.9, 0.1], 0, "1.000"),
    ],
)
def test_roc_saves_expected_auc_and_axis_labels(tmp_path, labels, scores, positive, expected):
    output = tmp_path / "artifacts" / "roc.svg"
    df = pl.DataFrame({"label": labels, "score": scores})
    assert plot_roc_curve(df, output=output, pos_label=positive) == output
    ET.parse(output)
    svg = output.read_text()
    assert f"ROC (AUC = {expected})" in svg
    assert "False positive rate" in svg
    assert "True positive rate" in svg
    assert "Chance" in svg


@pytest.mark.parametrize("plot", [plot_roc_curve, plot_score_histogram])
def test_png_style_is_fixed_without_changing_caller_settings_or_open_figures(
    tmp_path, monkeypatch, plot
):
    df = pl.DataFrame({"label": [0, 0, 1, 1], "score": [0.1, 0.4, 0.35, 0.8]})
    default_output = tmp_path / "default.png"
    output = tmp_path / "custom.png"
    output.write_bytes(b"old output")
    figures_before = pyplot.get_fignums()
    options = {"hue": "label"} if plot is plot_score_histogram else {}
    plot(df, output=default_output, **options)
    monkeypatch.setitem(mpl.rcParams, "backend", "svg")
    with mpl.rc_context(
        {"axes.facecolor": "black", "font.size": 30, "text.usetex": True, "savefig.dpi": 20}
    ):
        assert plot(df, output=str(output), **options) == output
        assert mpl.rcParams["axes.facecolor"] == "black"
        assert mpl.rcParams["text.usetex"] is True
        assert mpl.rcParams["backend"] == "svg"
    assert pyplot.get_fignums() == figures_before
    assert output.read_bytes() == default_output.read_bytes()
    pixels = image.imread(output)
    assert pixels.shape[:2] == (900, 900)
    assert pixels[:, :, :3].min() < 0.5


def test_pdf_output(tmp_path):
    output = tmp_path / "roc.pdf"
    df = pl.DataFrame({"actual": [0, 1], "prediction": [0.2, 0.8], "unused": [None, None]})
    original = df.clone()
    plot_roc_curve(df, label="actual", score="prediction", output=output)
    assert output.read_bytes().startswith(b"%PDF-")
    assert df.equals(original)


@pytest.mark.parametrize(
    ("labels", "scores", "positive"),
    [
        ([], [], 1),
        ([[0], [1]], [0.2, 0.8], 1),
        ([0, 1], [[0.8, 0.2], [0.2, 0.8]], 1),
        ([1, 1], [0.2, 0.8], 1),
        ([0, 1, 2], [0.2, 0.5, 0.8], 1),
        ([0.2, 0.8], [0.2, 0.8], 1),
        ([0, 1], [0.2, float("nan")], 1),
        ([0, 1], [0.2, float("inf")], 1),
        ([0.0, float("nan")], [0.2, 0.8], 1),
        ([0, None], [0.2, 0.8], 1),
        ([0, 1], [0.2, None], 1),
        ([0, 1], ["low", "high"], 1),
        ([0, 1], [0.2, 0.8], 2),
    ],
)
def test_invalid_data_does_not_create_output(tmp_path, labels, scores, positive):
    output = tmp_path / "artifacts" / "roc.png"
    df = pl.DataFrame({"label": labels, "score": scores})
    with pytest.raises(ValueError):
        plot_roc_curve(df, output=output, pos_label=positive)
    assert not output.parent.exists()


@pytest.mark.parametrize("hue", [None, "label"])
def test_histogram_preserves_counts_with_common_bins(tmp_path, monkeypatch, hue):
    df = pl.DataFrame(
        {"prediction": [1.0, 0.0, 0.0, 0.5, 0.0], "label": ["b", "a", "a", "b", "a"]}
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
    assert plot_score_histogram(df, score="prediction", hue=hue, output=output) == output
    assert df.equals(original)
    expected = np.array([[3, 0, 0, 0], [0, 0, 1, 1]])
    if hue is None:
        expected = expected.sum(axis=0)
    for counts, edges in observed:
        np.testing.assert_array_equal(counts, expected)
        np.testing.assert_allclose(edges, [0, 0.25, 0.5, 0.75, 1])
    assert observed
    svg = output.read_text()
    ET.parse(output)
    assert "Count" in svg
    if hue is None:
        assert "All (n = 5)" in svg
    else:
        assert "a (n = 3)" in svg
        assert "b (n = 2)" in svg
        assert svg.index("a (n = 3)") < svg.index("b (n = 2)")


def test_histogram_accepts_constant_scores_and_numeric_hue(tmp_path):
    df = pl.DataFrame({"score": [0.5, 0.5], "label": [1, 0]})
    output = tmp_path / "constant.svg"
    plot_score_histogram(df, hue="label", output=output)
    svg = output.read_text()
    assert "0 (n = 1)" in svg
    assert "1 (n = 1)" in svg


@pytest.mark.parametrize(
    "df",
    [
        pl.DataFrame({"score": [], "label": []}),
        pl.DataFrame({"label": [0, 1]}),
        pl.DataFrame({"score": [0.1, 0.9]}),
        pl.DataFrame({"score": [0.1, None], "label": [0, 1]}),
        pl.DataFrame({"score": [0.1, float("nan")], "label": [0, 1]}),
        pl.DataFrame({"score": [0.1, float("inf")], "label": [0, 1]}),
        pl.DataFrame({"score": ["low", "high"], "label": [0, 1]}),
        pl.DataFrame({"score": [0.1, 0.9], "label": [0, None]}),
        pl.DataFrame({"score": [0.1, 0.9], "label": [0.0, float("nan")]}),
        pl.DataFrame({"score": [0.1, 0.9], "label": [[0], [1]]}),
        pl.DataFrame({"score": range(21), "label": range(21)}),
    ],
)
def test_invalid_histogram_input_does_not_create_output(tmp_path, df):
    output = tmp_path / "artifacts" / "hist.png"
    with pytest.raises(ValueError):
        plot_score_histogram(df, hue="label", output=output)
    assert not output.parent.exists()


def test_unsupported_format_does_not_overwrite_output(tmp_path):
    output = tmp_path / "roc.txt"
    output.write_text("keep")
    with pytest.raises(ValueError, match="extension"):
        plot_roc_curve(pl.DataFrame({"label": [0, 1], "score": [0.2, 0.8]}), output=output)
    assert output.read_text() == "keep"


@pytest.mark.parametrize("column", ["label", "score"])
def test_missing_column_does_not_create_output(tmp_path, column):
    df = pl.DataFrame({"label": [0, 1], "score": [0.2, 0.8]}).drop(column)
    output = tmp_path / "artifacts" / "roc.png"
    with pytest.raises(ValueError, match="existing columns"):
        plot_roc_curve(df, output=output)
    assert not output.parent.exists()
