"""
chart_generator.py — Build colorful, meaningful Plotly charts from agent chart hints.

Charts render on the frontend's dark card surface, so all colors are the
dark-mode steps of a validated categorical palette (fixed slot order — the
ordering is the colorblind-safety mechanism, never re-shuffled or cycled).

Meaningfulness rules:
  - If the x column repeats, values are aggregated (mean by default; the agent
    can request sum/count via "using <agg>" in the chart hint).
  - Bars are sorted by value and capped at the top 12 categories.
  - Pies are capped at 7 slices + "Other" (more slices are unreadable).
  - Lines sort by x; scatter samples at most 1,000 points.
"""

import pandas as pd
import plotly.express as px

# Validated dark-mode categorical palette (fixed order)
_PALETTE = [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
    "#e66767",  # red
]
_INK_PRIMARY = "#ffffff"
_INK_SECONDARY = "#c3c2b7"
_GRID = "#2c2c2a"

_MAX_BAR_CATEGORIES = 12
_MAX_PIE_SLICES = 7  # plus "Other"


def _resolve_columns(df: pd.DataFrame, x: str, y: str) -> tuple[str, str]:
    """Map hint columns onto real DataFrame columns (case-insensitive)."""
    available = df.columns.tolist()
    col_map = {c.lower().strip(): c for c in available}
    x = col_map.get(x.lower().strip(), x.strip())
    y = col_map.get(y.lower().strip(), y.strip())
    if x not in available:
        x = available[0]
    if y not in available:
        y = available[1] if len(available) > 1 else available[0]
    return x, y


def _prepare(df: pd.DataFrame, x: str, y: str, agg: str, chart_type: str) -> pd.DataFrame:
    """Reduce raw rows to one meaningful value per category / point."""
    data = df[[x, y]].dropna() if x != y else df[[x]].dropna()

    y_numeric = x != y and pd.api.types.is_numeric_dtype(data[y])

    if chart_type == "scatter":
        # Raw relationship — no aggregation, just cap the point count
        return data.sample(1000, random_state=0) if len(data) > 1000 else data

    # Aggregate when the category column repeats (or y isn't numeric)
    if not y_numeric:
        data = data.groupby(x, dropna=False).size().reset_index(name=y if x != y else "count")
        if x == y:
            data.columns = [x, "count"]
    elif data[x].duplicated().any():
        agg_fn = {"sum": "sum", "count": "count", "mean": "mean"}.get(agg, "mean")
        data = data.groupby(x, dropna=False)[y].agg(agg_fn).reset_index()

    y_col = data.columns[1]
    if chart_type == "line":
        return data.sort_values(x)

    data = data.sort_values(y_col, ascending=False)
    if chart_type == "pie" and len(data) > _MAX_PIE_SLICES + 1:
        top = data.head(_MAX_PIE_SLICES)
        other = pd.DataFrame({x: ["Other"], y_col: [data[y_col].iloc[_MAX_PIE_SLICES:].sum()]})
        data = pd.concat([top, other], ignore_index=True)
    elif chart_type == "bar":
        data = data.head(_MAX_BAR_CATEGORIES)
    return data


def _apply_chrome(fig, title: str):
    fig.update_layout(
        title=dict(text=title, font=dict(color=_INK_PRIMARY, size=15)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=_INK_SECONDARY, family='system-ui, -apple-system, "Segoe UI", sans-serif'),
        margin=dict(l=48, r=24, t=48, b=44),
        hoverlabel=dict(bgcolor="#1a1a19", font_color=_INK_PRIMARY, bordercolor=_GRID),
    )
    fig.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID)
    fig.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID)
    return fig


def generate_chart(
    df: pd.DataFrame,
    chart_type: str,
    x: str,
    y: str,
    agg: str | None = None,
) -> str:
    """
    Build a Plotly chart and return it serialised as a JSON string.

    Args:
        df:         Source data — ideally the QUERY RESULT, not the raw table.
        chart_type: 'bar' | 'line' | 'pie' | 'scatter'
        x:          Category / x-axis column from the chart hint.
        y:          Value / y-axis column from the chart hint.
        agg:        Optional aggregation requested by the agent (sum|mean|count).
    """
    chart_type = chart_type.lower().strip()
    x, y = _resolve_columns(df, x, y)
    data = _prepare(df, x, y, (agg or "mean").lower(), chart_type)
    y_col = data.columns[1] if len(data.columns) > 1 else data.columns[0]

    if chart_type == "pie":
        fig = px.pie(
            data, names=x, values=y_col,
            title=f"{y_col} by {x}",
            color_discrete_sequence=_PALETTE,
            hole=0.35,
        )
        fig.update_traces(
            textinfo="percent+label",
            textfont_color=_INK_PRIMARY,
            marker=dict(line=dict(color="#1a1a19", width=2)),
        )
    elif chart_type == "line":
        fig = px.line(
            data, x=x, y=y_col,
            title=f"{y_col} over {x}",
            markers=True,
            color_discrete_sequence=[_PALETTE[0]],
        )
        fig.update_traces(line=dict(width=2), marker=dict(size=8))
    elif chart_type == "scatter":
        fig = px.scatter(
            data, x=x, y=y_col,
            title=f"{y_col} vs {x}",
            color_discrete_sequence=[_PALETTE[0]],
        )
        fig.update_traces(marker=dict(size=8, opacity=0.8))
    else:  # bar
        # Color per category (identity is on the axis; legend stays off).
        # Beyond the 8 palette slots, fall back to a single hue.
        colorful = len(data) <= len(_PALETTE)
        fig = px.bar(
            data, x=x, y=y_col,
            title=f"{y_col} by {x}",
            color=x if colorful else None,
            color_discrete_sequence=_PALETTE,
        )
        fig.update_layout(showlegend=False, bargap=0.25)
        fig.update_traces(marker_line_width=0)

    return _apply_chrome(fig, fig.layout.title.text).to_json()
