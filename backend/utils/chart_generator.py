import plotly.express as px
import pandas as pd


def generate_chart(df: pd.DataFrame, chart_type: str, x: str, y: str) -> str:
    """
    Build a Plotly chart from a DataFrame and return it as a JSON string
    that the frontend can deserialise with plotly.io.from_json().

    Args:
        df:         Source DataFrame
        chart_type: One of 'bar', 'line', 'pie', 'scatter'
        x:          Column name for the x-axis (or labels for pie)
        y:          Column name for the y-axis (or values for pie)

    Returns:
        Plotly figure serialised as a JSON string.
    """
    # Normalise column names — LLM may include extra spaces
    x = x.strip()
    y = y.strip()

    # Gracefully fall back to bar if columns don't exist
    available = df.columns.tolist()
    if x not in available or y not in available:
        # Try case-insensitive match
        col_map = {c.lower(): c for c in available}
        x = col_map.get(x.lower(), available[0])
        y = col_map.get(y.lower(), available[1] if len(available) > 1 else available[0])

    chart_type = chart_type.lower().strip()

    if chart_type == "pie":
        fig = px.pie(df, names=x, values=y, title=f"{y} by {x}")
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, title=f"{y} over {x}", markers=True)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, title=f"{y} vs {x}")
    else:  # default: bar
        fig = px.bar(df, x=x, y=y, title=f"{y} by {x}")

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#333333",
    )
    return fig.to_json()
