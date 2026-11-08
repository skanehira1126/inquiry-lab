"""Fixed visualizations for general data exploration."""

from pathlib import Path

import matplotlib as mpl
import numpy as np
import polars as pl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, PercentFormatter


def plot_histogram(
    df: pl.DataFrame,
    *,
    output: str | Path,
    column: str,
    hue: str | None = None,
) -> Path:
    """Save a histogram with horizontal box plots above a shared numeric axis.

    All groups share equal-width bin edges computed from all values using NumPy's
    ``auto`` rule (Sturges and Freedman-Diaconis). Groups are
    overlaid, not stacked or normalized; legend entries include their row counts.
    Hue values are treated as categories, sorted by value, with at most 20 groups.
    Nulls and non-finite values in selected columns are rejected, not dropped.
    The column must be numeric; hue values must be scalar and sortable.
    Each group's box shows the median and quartiles, with whiskers extending to
    the furthest observations within 1.5 IQR and points beyond them shown separately.

    Save PNG (900 x 900 px), SVG, or PDF, creating parents and overwriting the
    output file. Return its Path without changing df or exposing plotting options.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    values = _numeric_values(df, column)
    frames, names = _plot_groups(df, hue)
    groups = [np.asarray(frame.get_column(column).to_numpy(), dtype=float) for frame in frames]

    bins = np.histogram_bin_edges(values, bins="auto")
    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        box_ax, ax = figure.subplots(
            2, 1, sharex=True, height_ratios=[max(1, len(groups) * 0.25), 3]
        )
        palette = mpl.colormaps["tab10" if len(groups) <= 10 else "tab20"]
        colors = [palette(index) for index in range(len(groups))]
        for position, (group, color) in enumerate(zip(groups, colors, strict=True), start=1):
            box_ax.boxplot(
                group,
                positions=[position],
                orientation="horizontal",
                whis=1.5,
                widths=0.6,
                patch_artist=True,
                manage_ticks=False,
                boxprops={"facecolor": color, "edgecolor": color, "alpha": 0.3},
                medianprops={"color": color, "linewidth": 1.5},
                whiskerprops={"color": color},
                capprops={"color": color},
                flierprops={"marker": "o", "markersize": 3, "markeredgecolor": color},
            )
        box_ax.set(title="Distribution", ylim=(len(groups) + 0.5, 0.5))
        box_ax.set_yticks(range(1, len(groups) + 1), labels=names, fontsize=8)
        box_ax.tick_params(axis="x", bottom=False)
        box_ax.grid(visible=True, axis="x", color="#e5e7eb", linewidth=0.8)
        box_ax.set_axisbelow(True)
        ax.hist(
            groups,
            bins=bins,
            histtype="stepfilled",
            alpha=0.3,
            color=colors,
            label=names,
        )
        ax.hist(groups, bins=bins, histtype="step", linewidth=1.5, color=colors)
        ax.set(xlabel=column, ylabel="Count", ylim=(0, None))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(visible=True, axis="y", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        handles, legend_labels = ax.get_legend_handles_labels()
        handles_by_label = dict(zip(legend_labels, handles, strict=True))
        ax.legend(
            handles=[handles_by_label[name] for name in names],
            title=hue,
            loc="best",
            ncols=(len(groups) + 4) // 5,
            fontsize=8,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output


def plot_scatter(
    df: pl.DataFrame,
    *,
    output: str | Path,
    x: str,
    y: str,
    hue: str | None = None,
) -> Path:
    """Save paired numeric observations as a scatter plot, optionally colored by group.

    Plot every row without sampling, aggregation, jitter, or a fitted trend.
    Both axes must contain finite numeric values with no nulls. Hue is categorical
    even for numeric values; groups are sorted by value, limited to 20, and labeled
    with row counts. Nulls, non-finite floats, and nested/object hue values are rejected.
    The plotting area is square; the two axes retain independent numeric scales.

    Save PNG (900 x 900 px), SVG, or PDF, creating parents and overwriting output.
    Return its Path without changing df, caller styles, or open pyplot figures.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    _numeric_values(df, x)
    _numeric_values(df, y)
    groups, names = _plot_groups(df, hue)

    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        palette = mpl.colormaps["tab10" if len(groups) <= 10 else "tab20"]
        for index, (group, name) in enumerate(zip(groups, names, strict=True)):
            ax.scatter(
                np.asarray(group.get_column(x).to_numpy(), dtype=float),
                np.asarray(group.get_column(y).to_numpy(), dtype=float),
                color=palette(index),
                s=20,
                alpha=0.6,
                linewidths=0,
                label=name,
            )
        ax.set(title="Scatter plot", xlabel=x, ylabel=y, box_aspect=1)
        ax.grid(visible=True, color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(title=hue, loc="best", ncols=(len(groups) + 4) // 5, fontsize=8)
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output


def plot_count(
    df: pl.DataFrame,
    *,
    output: str | Path,
    column: str,
    hue: str | None = None,
    count: str | None = None,
    normalize: bool = False,
) -> Path:
    """Save horizontal category counts, optionally grouped or normalized.

    Count each input row once unless ``count`` names a non-negative integer
    count column. Sum supplied counts for repeated categories within each hue
    group; aggregated input is never detected automatically. With ``normalize``,
    divide by each group's total count. Zero-total groups have undefined shares
    and are rejected in normalized mode.

    Categories and hue groups are sorted by value, each limited to 20. Numeric
    category values remain categories. Missing combinations are shown as zero;
    nulls, non-finite values, and nested/object categories are rejected.
    Hue bars are side by side and legend counts reflect total observations,
    including for aggregated inputs. All categories are shown without truncation.

    Save PNG (900 x 900 px), SVG, or PDF, creating parents and overwriting output.
    Return its Path without changing df, caller styles, or open pyplot figures.
    Invalid inputs raise ValueError before creating directories or saving a file.
    """
    output = Path(output)
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("output must have a .png, .svg, or .pdf extension")
    if df.is_empty():
        raise ValueError("df must contain at least one row")
    categories = _category_values(df, column)
    if len(categories) > 20:
        raise ValueError("column must contain at most 20 categories")
    if count is not None:
        if count not in df.columns:
            raise ValueError("count must name an existing column")
        weights = df.get_column(count)
        if weights.null_count() or not weights.dtype.is_integer() or (weights < 0).any():
            raise ValueError("count column must contain non-negative integers with no nulls")

    groups, _ = _plot_groups(df, hue)
    group_counts = []
    names = []
    for group in groups:
        if count is None:
            data = group.select(category=pl.col(column)).group_by("category").agg(total=pl.len())
        else:
            data = group.select(category=pl.col(column), total=pl.col(count))
        totals = {value: 0 for value in categories}
        for value, weight in data.iter_rows():
            totals[value] += weight
        total = sum(totals.values())
        if normalize and not total:
            raise ValueError("each group must have a positive total count to normalize")
        group_counts.append([value / total if normalize else value for value in totals.values()])
        name = "All" if hue is None else str(group.get_column(hue)[0])
        names.append(f"{name} (n = {total:,})")

    style = {key: value for key, value in mpl.rcParamsDefault.items() if key != "backend"}
    with mpl.rc_context(rc=style):
        figure = Figure(figsize=(6, 6), dpi=150, layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        palette = mpl.colormaps["tab10" if len(groups) <= 10 else "tab20"]
        positions = np.arange(len(categories))
        height = 0.8 / len(groups)
        for index, (values, name) in enumerate(zip(group_counts, names, strict=True)):
            ax.barh(
                positions + (index - (len(groups) - 1) / 2) * height,
                values,
                height=height,
                color=palette(index),
                alpha=0.8,
                label=name,
            )
        ax.set_yticks(positions, labels=[str(value) for value in categories], fontsize=9)
        ax.set(
            title="Category proportions" if normalize else "Category counts",
            xlabel="Share within each group" if normalize else "Count",
            ylabel=column,
            xlim=(0, 1 if normalize else None),
            ylim=(len(categories) - 0.5, -0.5),
        )
        if normalize:
            ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
        else:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(visible=True, axis="x", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.legend(title=hue, loc="best", ncols=(len(groups) + 4) // 5, fontsize=8)
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, format=output.suffix[1:].lower(), dpi=150)

    return output


def _numeric_values(df: pl.DataFrame, column: str) -> np.ndarray:
    if column not in df.columns:
        raise ValueError(f"column {column!r} must name an existing column")
    if df.is_empty():
        raise ValueError("df must contain at least one row")
    values = df.get_column(column)
    if values.null_count() or not values.dtype.is_numeric():
        raise ValueError(f"column {column!r} must be numeric and contain no nulls")
    array = np.asarray(values.to_numpy(), dtype=float)
    if not np.isfinite(array).all():
        raise ValueError(f"column {column!r} must contain only finite values")
    return array


def _plot_groups(df: pl.DataFrame, hue: str | None) -> tuple[list[pl.DataFrame], list[str]]:
    if hue is None:
        return [df], [f"All (n = {len(df):,})"]
    categories = _category_values(df, hue)
    if len(categories) > 20:
        raise ValueError("hue column must contain at most 20 groups")
    groups = [df.filter(pl.col(hue) == value) for value in categories]
    names = [
        f"{value} (n = {len(group):,})" for value, group in zip(categories, groups, strict=True)
    ]
    return groups, names


def _category_values(df: pl.DataFrame, column: str) -> list:
    if column not in df.columns:
        raise ValueError(f"column {column!r} must name an existing column")
    values = df.get_column(column)
    if values.null_count():
        raise ValueError(f"column {column!r} must not contain nulls")
    if values.dtype.is_nested() or values.dtype == pl.Object:
        raise ValueError(f"column {column!r} must contain sortable scalar values")
    if values.dtype.is_float() and not values.is_finite().all():
        raise ValueError(f"column {column!r} must contain only finite values")
    return values.unique().sort().to_list()
