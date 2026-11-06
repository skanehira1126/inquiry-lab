"""Fixed visualizations for general data exploration."""

from pathlib import Path

import matplotlib as mpl
import numpy as np
import polars as pl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


def plot_histogram(
    df: pl.DataFrame,
    *,
    output: str | Path,
    column: str,
    hue: str | None = None,
) -> Path:
    """Save a numeric column's counts in automatic bins, optionally colored by a column.

    All groups share equal-width bin edges computed from all values using NumPy's
    ``auto`` rule (Sturges and Freedman-Diaconis). Groups are
    overlaid, not stacked or normalized; legend entries include their row counts.
    Hue values are treated as categories, sorted by value, with at most 20 groups.
    Nulls and non-finite values in selected columns are rejected, not dropped.
    The column must be numeric; hue values must be scalar and sortable.

    Save PNG (900 x 900 px), SVG, or PDF, creating parents and overwriting the
    output file. Return its Path without changing df or exposing plotting options.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    if column not in df.columns or (hue is not None and hue not in df.columns):
        raise ValueError("column and hue must name existing columns")
    column_values = df.get_column(column)
    if df.is_empty():
        raise ValueError("df must contain at least one row")
    if column_values.null_count() or not column_values.dtype.is_numeric():
        raise ValueError("selected column must be numeric and contain no nulls")
    values = np.asarray(column_values.to_numpy(), dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("selected column must contain only finite values")

    groups = [values]
    names = [f"All (n = {len(values):,})"]
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
            np.asarray(df.filter(pl.col(hue) == value).get_column(column).to_numpy(), dtype=float)
            for value in categories
        ]
        names = [
            f"{value} (n = {len(group):,})"
            for value, group in zip(categories, groups, strict=True)
        ]

    bins = np.histogram_bin_edges(values, bins="auto")
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
        ax.set(title="Distribution", xlabel=column, ylabel="Count", ylim=(0, None))
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
