"""
Reusable Plotly chart functions for the Fitness Tracker app.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta


def calorie_bar_chart(df: pd.DataFrame, target: float = 2500.0):
    """Daily calories vs. target bar chart.

    Args:
        df: DataFrame with columns ['date', 'calories']
        target: Daily calorie target
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Daily Calories vs Target")
        return fig

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["date"], y=df["calories"], name="Calories Eaten", marker_color="steelblue"))
    fig.add_hline(y=target, line_dash="dash", line_color="red", annotation_text=f"Target: {target} kcal")
    fig.update_layout(title="Daily Calories vs Target", xaxis_title="Date", yaxis_title="Calories (kcal)")
    return fig


def macro_pie_chart(protein: float, carbs: float, fat: float):
    """Macro breakdown pie chart."""
    labels = ["Protein", "Carbs", "Fat"]
    values = [protein * 4, carbs * 4, fat * 9]  # calories from each macro
    colors = ["#2196F3", "#FF9800", "#F44336"]

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4,
                                  marker=dict(colors=colors))])
    fig.update_layout(title="Macro Breakdown (by calories)")
    return fig


def weight_trend_chart(df: pd.DataFrame):
    """Weight trend line with 7-day moving average.

    Args:
        df: DataFrame with columns ['date', 'weight_kg']
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Weight Trend")
        return fig

    df = df.sort_values("date")
    df["ma7"] = df["weight_kg"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["weight_kg"], mode="lines+markers",
                              name="Weight", line=dict(color="steelblue")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma7"], mode="lines",
                              name="7-day MA", line=dict(color="orange", dash="dash")))
    fig.update_layout(title="Weight Trend", xaxis_title="Date", yaxis_title="Weight (kg)")
    return fig


def muscle_volume_chart(df: pd.DataFrame):
    """Sets per muscle group bar chart.

    Args:
        df: DataFrame with columns ['muscle_group', 'sets']
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Weekly Volume by Muscle Group")
        return fig

    recommended = {
        "chest": (10, 20), "back": (10, 20), "legs": (12, 20),
        "shoulders": (8, 16), "arms": (6, 14), "core": (6, 14), "full_body": (10, 20)
    }

    fig = go.Figure()
    colors = []
    for _, row in df.iterrows():
        mg = row["muscle_group"]
        sets = row["sets"]
        low, high = recommended.get(mg, (8, 16))
        if sets < low:
            colors.append("orange")
        elif sets > high:
            colors.append("red")
        else:
            colors.append("green")

    fig.add_trace(go.Bar(x=df["muscle_group"], y=df["sets"], marker_color=colors, name="Sets"))
    fig.update_layout(title="Weekly Volume by Muscle Group", xaxis_title="Muscle Group", yaxis_title="Sets")
    return fig


def digestion_timeline_chart(active_digestions: list):
    """Horizontal bar 'stomach queue' visualization.

    Args:
        active_digestions: list of dicts with keys:
            food_name, start_time (datetime), end_time (datetime), percent_complete
    """
    if not active_digestions:
        fig = go.Figure()
        fig.add_annotation(text="No active digestion", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Digestion Timeline")
        return fig

    fig = go.Figure()
    for i, item in enumerate(active_digestions):
        pct = item.get("percent_complete", 0)
        color = f"rgba(33, 150, 243, {0.3 + 0.7 * pct / 100})"
        fig.add_trace(go.Bar(
            x=[item["end_time"] - item["start_time"]],
            y=[item["food_name"]],
            base=[item["start_time"]],
            orientation="h",
            marker_color=color,
            name=item["food_name"],
            text=f"{pct:.0f}% digested",
            textposition="inside",
        ))

    fig.update_layout(
        title="Active Digestion Timeline",
        barmode="overlay",
        xaxis_title="Time",
        yaxis_title="Food",
    )
    return fig


def cycle_gantt_chart(compounds: list):
    """Plotly Gantt chart for cycle planning.

    Args:
        compounds: list of dicts with keys: name, start_date, end_date, type
    """
    if not compounds:
        fig = go.Figure()
        fig.add_annotation(text="No compounds defined", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Cycle Planner")
        return fig

    df = pd.DataFrame(compounds)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    color_map = {"anabolic": "steelblue", "peptide": "green", "sarm": "orange", "other": "gray"}

    fig = px.timeline(
        df,
        x_start="start_date",
        x_end="end_date",
        y="name",
        color="type",
        color_discrete_map=color_map,
        title="Compound Cycle Gantt",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Compound")
    return fig


def bloodwork_status_table(df: pd.DataFrame):
    """Color-coded bloodwork marker table.

    Args:
        df: DataFrame with columns ['marker_name', 'value', 'unit', 'reference_min', 'reference_max']
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No bloodwork data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    def get_color(row):
        try:
            v, low, high = float(row["value"]), float(row["reference_min"]), float(row["reference_max"])
            if low <= v <= high:
                return "lightgreen"
            margin = (high - low) * 0.1
            if (low - margin) <= v <= (high + margin):
                return "lightyellow"
            return "lightcoral"
        except (TypeError, ValueError):
            return "white"

    fill_colors = [df.apply(get_color, axis=1).tolist()]

    fig = go.Figure(data=[go.Table(
        header=dict(values=list(df.columns), fill_color="steelblue", font=dict(color="white")),
        cells=dict(
            values=[df[c].tolist() for c in df.columns],
            fill_color=fill_colors * len(df.columns),
        )
    )])
    fig.update_layout(title="Bloodwork Markers Dashboard")
    return fig


def wellbeing_trends_chart(df: pd.DataFrame):
    """Multi-line wellbeing metrics chart.

    Args:
        df: DataFrame with columns ['date', 'mood_score', 'energy_score', 'sleep_quality', 'libido_score']
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data yet", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title="Wellbeing Trends")
        return fig

    fig = go.Figure()
    metric_colors = {
        "mood_score": "blue",
        "energy_score": "orange",
        "sleep_quality": "purple",
        "libido_score": "red",
    }
    for metric, color in metric_colors.items():
        if metric in df.columns:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[metric],
                mode="lines+markers",
                name=metric.replace("_", " ").title(),
                line=dict(color=color),
            ))

    fig.update_layout(
        title="Wellbeing Trends",
        xaxis_title="Date",
        yaxis_title="Score (1–10)",
        yaxis=dict(range=[0, 11]),
    )
    return fig
