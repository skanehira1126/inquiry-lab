import xml.etree.ElementTree as ET

import matplotlib as mpl
import numpy as np
import polars as pl
import pytest
from matplotlib import image, pyplot
from matplotlib.figure import Figure

from inquiry_lab.visualize.ml.classifier import (
    plot_calibration_curve,
    plot_roc_curve,
)


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


@pytest.mark.parametrize("plot", [plot_roc_curve, plot_calibration_curve])
def test_png_style_is_fixed_without_changing_caller_settings_or_open_figures(
    tmp_path, monkeypatch, plot
):
    df = pl.DataFrame({"label": [0, 0, 1, 1], "score": [0.1, 0.4, 0.35, 0.8]})
    default_output = tmp_path / "default.png"
    output = tmp_path / "custom.png"
    output.write_bytes(b"old output")
    figures_before = pyplot.get_fignums()
    plot(df, output=default_output)
    monkeypatch.setitem(mpl.rcParams, "backend", "svg")
    with mpl.rc_context(
        {"axes.facecolor": "black", "font.size": 30, "text.usetex": True, "savefig.dpi": 20}
    ):
        assert plot(df, output=str(output)) == output
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
def test_roc_rejects_invalid_binary_inputs_before_creating_output(
    tmp_path, labels, scores, positive
):
    # ROC owns the full input matrix shared with calibration.
    output = tmp_path / "artifacts" / "roc.png"
    df = pl.DataFrame({"label": labels, "score": scores})
    with pytest.raises(ValueError):
        plot_roc_curve(df, output=output, pos_label=positive)
    assert not output.parent.exists()


def test_calibration_requires_both_classes_before_creating_output(tmp_path):
    output = tmp_path / "artifacts" / "calibration.png"
    df = pl.DataFrame({"label": [1, 1], "score": [0.2, 0.8]})
    with pytest.raises(ValueError, match="exactly two classes"):
        plot_calibration_curve(df, output=output)
    assert not output.parent.exists()


@pytest.mark.parametrize("plot", [plot_roc_curve, plot_calibration_curve])
def test_unsupported_format_does_not_overwrite_output(tmp_path, plot):
    output = tmp_path / "roc.txt"
    output.write_text("keep")
    with pytest.raises(ValueError, match="extension"):
        plot(pl.DataFrame({"label": [0, 1], "score": [0.2, 0.8]}), output=output)
    assert output.read_text() == "keep"


@pytest.mark.parametrize("column", ["label", "score"])
@pytest.mark.parametrize("plot", [plot_roc_curve, plot_calibration_curve])
def test_missing_column_does_not_create_output(tmp_path, column, plot):
    df = pl.DataFrame({"label": [0, 1], "score": [0.2, 0.8]}).drop(column)
    output = tmp_path / "artifacts" / "roc.png"
    with pytest.raises(ValueError, match="existing columns"):
        plot(df, output=output)
    assert not output.parent.exists()


@pytest.mark.parametrize(("negative", "positive"), [(0, 1), ("no", "yes"), (1, 0)])
def test_calibration_curve_and_counts_share_bins(tmp_path, monkeypatch, negative, positive):
    df = pl.DataFrame(
        {
            "actual": [negative, positive, positive, negative, positive, positive, negative],
            "probability": [0.0, 0.04, 0.1, 0.15, 0.8, 0.9, 1.0],
        }
    )
    original = df.clone()
    savefig = Figure.savefig
    figures = []

    def capture(self, *args, **kwargs):
        figures.append(self)
        return savefig(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    output = tmp_path / "artifacts" / "calibration.svg"
    assert (
        plot_calibration_curve(
            df, label="actual", score="probability", pos_label=positive, output=output
        )
        == output
    )
    assert df.equals(original)
    figure = figures[0]
    curve_ax = next(ax for ax in figure.axes if ax.get_ylabel() == "Observed positive rate")
    count_ax = next(ax for ax in figure.axes if ax.get_ylabel() == "Samples per bin")
    curve = next(line for line in curve_ax.lines if line.get_label() == "Calibration")
    np.testing.assert_allclose(
        curve.get_xdata(), [0.14 / 3, 0.15, np.nan, np.nan, np.nan, np.nan, np.nan, 0.8, 0.9, 1]
    )
    np.testing.assert_allclose(
        curve.get_ydata(), [2 / 3, 0, np.nan, np.nan, np.nan, np.nan, np.nan, 1, 1, 0]
    )
    bars = next(item for item in count_ax.containers if item.get_label() == "Samples per bin")
    assert [bar.get_height() for bar in bars] == [3, 1, 0, 0, 0, 0, 0, 1, 1, 1]
    np.testing.assert_allclose([bar.get_x() for bar in bars], np.arange(10) / 10)
    np.testing.assert_allclose([bar.get_width() for bar in bars], 0.1)
    assert curve_ax.get_shared_x_axes().joined(curve_ax, count_ax)
    assert not curve_ax.get_shared_y_axes().joined(curve_ax, count_ax)
    ET.parse(output)
    svg = output.read_text()
    assert "Calibration" in svg
    assert "Samples per bin" in svg
    assert "Ideal" in svg


@pytest.mark.parametrize("scores", [[-0.01, 0.8], [0.2, 1.01]])
def test_calibration_rejects_scores_outside_probability_range(tmp_path, scores):
    output = tmp_path / "artifacts" / "calibration.png"
    with pytest.raises(ValueError, match="probabilities"):
        plot_calibration_curve(pl.DataFrame({"label": [0, 1], "score": scores}), output=output)
    assert not output.parent.exists()
