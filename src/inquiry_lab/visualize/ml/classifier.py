"""Fixed plots for classifier evaluation."""

from pathlib import Path

import matplotlib as mpl
import numpy as np
import polars as pl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from sklearn.metrics import auc, roc_curve
from sklearn.utils.multiclass import type_of_target


def plot_roc_curve(
    df: pl.DataFrame,
    *,
    output: str | Path,
    label: str = "label",
    score: str = "score",
    pos_label: int | float | bool | str = 1,
) -> Path:
    """Save a binary ROC curve with AUC; return the output path.

    Select the true-label and prediction-score columns from a Polars DataFrame.
    Both classes must be present. Scores must be finite numeric values that
    increase toward ``pos_label`` (positive-class probabilities or decision scores).
    Nulls and NaNs in either selected column are rejected, not dropped.
    Positive labels other than 1 require ``pos_label``. The input is not modified.

    Save PNG (150 dpi), SVG, or PDF according to the required file extension.
    Parent directories are created and existing output files are overwritten.
    Styling is fixed and independent of the caller's matplotlib settings.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")

    labels, scores = _binary_scores(df, label, score, pos_label)
    fpr, tpr, _ = roc_curve(labels, scores, pos_label=pos_label)
    roc_auc = auc(fpr, tpr)

    # Reset caller styles locally so the same inputs retain the same presentation.
    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        ax.plot(fpr, tpr, color="#2563eb", linewidth=2, label=f"ROC (AUC = {roc_auc:.3f})")
        ax.plot([0, 1], [0, 1], color="#9ca3af", linewidth=1, linestyle="--", label="Chance")
        ax.set(
            title="ROC curve",
            xlabel="False positive rate",
            ylabel="True positive rate",
            xlim=(-0.02, 1.02),
            ylim=(-0.02, 1.02),
            aspect="equal",
        )
        ax.set_xticks(np.linspace(0, 1, 6))
        ax.set_yticks(np.linspace(0, 1, 6))
        ax.grid(visible=True, color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(loc="lower right")
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output


def plot_calibration_curve(
    df: pl.DataFrame,
    *,
    output: str | Path,
    label: str = "label",
    score: str = "score",
    pos_label: int | float | bool | str = 1,
) -> Path:
    """Save binary calibration with overlaid sample counts on a separate right axis.

    Use ten equal-width probability bins from 0 to 1. The curve shows each bin's
    mean predicted probability and observed positive rate; background bars and
    their annotations show counts from exactly the same assignments. Bins include
    their right edge, with 0 included in the first bin. Empty bins have no point
    and break the curve rather than implying a zero positive rate.

    Inputs follow plot_roc_curve's column and positive-label contract, but scores
    must be probabilities in [0, 1]. Both classes are required; nulls and non-finite
    values are rejected. Save PNG (900 x 900 px), SVG, or PDF, creating parents and
    overwriting output. Return its Path without modifying df or caller styles.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    labels, scores = _binary_scores(df, label, score, pos_label)
    if ((scores < 0) | (scores > 1)).any():
        raise ValueError("calibration scores must be probabilities between 0 and 1")

    edges = np.linspace(0, 1, 11)
    # Share assignments so curve denominators and bars agree at every bin edge.
    bin_ids = np.searchsorted(edges[1:-1], scores, side="left")
    counts = np.bincount(bin_ids, minlength=10)
    score_sums = np.bincount(bin_ids, weights=scores, minlength=10)
    positives = np.bincount(bin_ids, weights=labels == pos_label, minlength=10)
    nonempty = counts > 0
    mean_score = np.full(10, np.nan)
    positive_rate = np.full(10, np.nan)
    np.divide(score_sums, counts, out=mean_score, where=nonempty)
    np.divide(positives, counts, out=positive_rate, where=nonempty)

    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        count_ax = ax.twinx()
        bars = count_ax.bar(
            edges[:-1],
            counts,
            width=np.diff(edges),
            align="edge",
            color="#9ca3af",
            alpha=0.25,
            edgecolor="white",
            label="Samples per bin",
        )
        count_ax.set(ylabel="Samples per bin", ylim=(0, counts.max() * 1.3))
        count_ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        count_ax.tick_params(axis="y", colors="#6b7280")
        count_ax.yaxis.label.set_color("#6b7280")
        count_ax.grid(visible=False)
        ax.set_zorder(count_ax.get_zorder() + 1)
        ax.patch.set_visible(False)
        ax.plot(
            mean_score,
            positive_rate,
            color="#2563eb",
            marker="o",
            linewidth=2,
            label="Calibration",
        )
        ax.plot([0, 1], [0, 1], color="#9ca3af", linestyle="--", label="Ideal")
        ax.set(
            title="Calibration curve",
            xlabel="Predicted probability",
            ylabel="Observed positive rate",
            xlim=(-0.02, 1.02),
            ylim=(-0.02, 1.02),
        )
        ax.set_xticks(np.linspace(0, 1, 6))
        ax.set_yticks(np.linspace(0, 1, 6))
        ax.grid(visible=True, color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        for bar, count in zip(bars, counts, strict=True):
            if count:
                ax.annotate(
                    f"{count:,}",
                    xy=(bar.get_x() + bar.get_width() / 2, count),
                    xycoords=count_ax.transData,
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                    color="#6b7280",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1},
                )
        ax.legend(handles=[*ax.lines, bars], loc="upper left")
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output


def _binary_scores(
    df: pl.DataFrame, label: str, score: str, pos_label: int | float | bool | str
) -> tuple[np.ndarray, np.ndarray]:
    """Validate the shared binary-label and finite-score input contract."""
    if label not in df.columns or score not in df.columns:
        raise ValueError("label and score must name existing columns")
    label_values = df.get_column(label)
    score_values = df.get_column(score)
    if df.is_empty():
        raise ValueError("df must contain at least one row")
    if label_values.null_count() or score_values.null_count():
        raise ValueError("label and score columns must not contain nulls")
    if not score_values.dtype.is_numeric():
        raise ValueError("score column must be numeric")
    labels = label_values.to_numpy()
    scores = np.asarray(score_values.to_numpy(), dtype=float)
    if labels.ndim != 1 or scores.ndim != 1:
        raise ValueError("label and score columns must contain scalar values")
    if not np.isfinite(scores).all():
        raise ValueError("score column must contain only finite values")
    if np.issubdtype(labels.dtype, np.number) and not np.isfinite(labels).all():
        raise ValueError("label column must contain only finite values")
    if type_of_target(labels) != "binary" or len(np.unique(labels)) != 2:
        raise ValueError("label column must contain exactly two classes")
    if pos_label not in labels:
        raise ValueError("pos_label must be one of the two classes in the label column")
    return labels, scores


def plot_score_histogram(
    df: pl.DataFrame,
    *,
    output: str | Path,
    score: str = "score",
    hue: str | None = None,
) -> Path:
    """Save score counts in automatic bins, optionally colored by a column.

    All groups share equal-width bin edges computed from all scores using NumPy's
    ``auto`` rule (Sturges and Freedman-Diaconis). Groups are
    overlaid, not stacked or normalized; legend entries include their row counts.
    Hue values are treated as categories, sorted by value, with at most 20 groups.
    Nulls and non-finite values in selected columns are rejected, not dropped.
    Scores must be numeric; hue values must be scalar and sortable.

    Save PNG (900 x 900 px), SVG, or PDF, creating parents and overwriting the
    output file. Return its Path without changing df or exposing plotting options.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    if score not in df.columns or (hue is not None and hue not in df.columns):
        raise ValueError("score and hue must name existing columns")
    score_values = df.get_column(score)
    if df.is_empty():
        raise ValueError("df must contain at least one row")
    if score_values.null_count() or not score_values.dtype.is_numeric():
        raise ValueError("score column must be numeric and contain no nulls")
    scores = np.asarray(score_values.to_numpy(), dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError("score column must contain only finite values")

    groups = [scores]
    names = [f"All (n = {len(scores):,})"]
    if hue is not None:
        hue_values = df.get_column(hue)
        if hue_values.null_count():
            raise ValueError("hue column must not contain nulls")
        if hue_values.dtype.is_nested() or hue_values.dtype == pl.Object:
            raise ValueError("hue column must contain sortable scalar values")
        if hue_values.dtype.is_float() and not hue_values.is_finite().all():
            raise ValueError("hue column must contain only finite values")
        categories = hue_values.unique().sort().to_list()
        if len(categories) > 20:
            raise ValueError("hue column must contain at most 20 groups")
        groups = [
            np.asarray(df.filter(pl.col(hue) == value).get_column(score).to_numpy(), dtype=float)
            for value in categories
        ]
        names = [
            f"{value} (n = {len(group):,})"
            for value, group in zip(categories, groups, strict=True)
        ]

    bins = np.histogram_bin_edges(scores, bins="auto")
    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        palette = mpl.colormaps["tab10" if len(groups) <= 10 else "tab20"]
        colors = [palette(index) for index in range(len(groups))]
        ax.hist(
            groups,
            bins=bins,
            histtype="stepfilled",
            alpha=0.3,
            color=colors,
            label=names,
        )
        ax.hist(groups, bins=bins, histtype="step", linewidth=1.5, color=colors)
        ax.set(title="Score distribution", xlabel="Score", ylabel="Count", ylim=(0, None))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(visible=True, axis="y", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        handles, legend_labels = ax.get_legend_handles_labels()
        handles_by_label = dict(zip(legend_labels, handles, strict=True))
        ax.legend(
            handles=[handles_by_label[name] for name in names],
            title=hue,
            loc="upper left",
            bbox_to_anchor=(1, 1),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output
