"""Altair chart builders for the Dashboard, in the printed-report style.

Colours come from tracker.styles.TOKENS; axis/grid styling comes from the
registered Altair theme (see styles._altair_theme). Render each chart with
``st.altair_chart(chart, width="stretch", theme=None)``.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from .db import STATUSES
from .styles import TOKENS

# Olive from light to dark across the forward stages; closed outcomes in warm gray.
STAGE_COLORS = {
    "Wishlist":  "#C9D0BC",
    "Applied":   "#A9B39D",
    "OA/Screen": "#8A957F",
    "Interview": "#6B7761",
    "Offer":     "#4E5947",
    "Rejected":  "#B5ACA0",
    "Withdrawn": "#D3CCC1",
}


def _fmt_day(ts: pd.Timestamp) -> str:
    """"Nov 9" (no zero padding, works on every platform)."""
    return f"{ts:%b} {ts.day}"


def pipeline_chart(status_counts: pd.Series) -> alt.Chart:
    """Horizontal bars in pipeline order, count labels at the end of each bar."""
    data = pd.DataFrame({
        "stage": STATUSES,
        "count": [int(status_counts.get(s, 0)) for s in STATUSES],
    })
    data["tip"] = data.apply(
        lambda r: f"{r.stage} — {r['count']} application{'s' if r['count'] != 1 else ''}",
        axis=1,
    )
    y = alt.Y("stage:N", sort=STATUSES, title=None,
              axis=alt.Axis(grid=False, labelColor=TOKENS["text"], labelFontSize=12,
                            labelPadding=10))
    base = alt.Chart(data).encode(y=y)
    bars = base.mark_bar(height=16, cornerRadiusEnd=2).encode(
        x=alt.X("count:Q", title=None, axis=None,
                scale=alt.Scale(domain=[0, max(int(data["count"].max()), 1) * 1.15])),
        color=alt.Color("stage:N", scale=alt.Scale(domain=list(STAGE_COLORS),
                                                   range=list(STAGE_COLORS.values())),
                        legend=None),
        tooltip=alt.Tooltip("tip:N"),
        description=alt.Description("tip:N"),
    )
    labels = base.mark_text(align="left", dx=6, aria=False, color=TOKENS["text"]).encode(
        x="count:Q", text="count:Q",
    )
    return (bars + labels).properties(height=len(STATUSES) * 30)


def weekly_chart(weekly: pd.DataFrame, goal: int) -> alt.Chart:
    """Vertical bars per week with a dashed goal line.

    *weekly* is analytics.weekly_counts() output (week_start, count).
    """
    data = weekly.copy()
    data["week"] = data["week_start"].map(_fmt_day)
    data["tip"] = data.apply(
        lambda r: f"Week of {r.week} — {r['count']} application{'s' if r['count'] != 1 else ''}",
        axis=1,
    )
    order = list(data["week"])
    top = max(int(data["count"].max()), int(goal), 1)
    x = alt.X("week:N", sort=order, title=None,
              # Label every other week, always including the current one.
              axis=alt.Axis(values=order[(len(order) - 1) % 2::2]))
    y = alt.Y("count:Q", title=None,
              scale=alt.Scale(domain=[0, top * 1.1], nice=False),
              axis=alt.Axis(tickMinStep=1, format="d"))
    bars = alt.Chart(data).mark_bar(
        width={"band": 0.45}, cornerRadiusTopLeft=2, cornerRadiusTopRight=2,
        color=TOKENS["olive"],
    ).encode(x=x, y=y, tooltip=alt.Tooltip("tip:N"), description=alt.Description("tip:N"))
    goal_df = pd.DataFrame({"goal": [goal], "tip": [f"Weekly goal — {goal}"]})
    goal_rule = alt.Chart(goal_df).mark_rule(
        strokeDash=[4, 4], strokeWidth=1, color=TOKENS["olive_mid"],
    ).encode(y="goal:Q", tooltip=alt.Tooltip("tip:N"))
    goal_label = alt.Chart(goal_df).mark_text(
        align="right", baseline="bottom", dy=-4, x="width", fontSize=10,
        color=TOKENS["muted"],
    ).encode(y="goal:Q", text=alt.value(f"goal {goal}"))
    return (bars + goal_rule + goal_label).properties(height=200)


def response_rate_chart(rbs: pd.DataFrame) -> alt.Chart:
    """Ranked horizontal bars: response rate by source.

    *rbs* is analytics.response_by_source() output.
    """
    data = rbs.copy()
    data["pct"] = (data["rate"] * 100).round().astype(int)
    data["label"] = data.apply(
        lambda r: f"{r.pct}%  ·  {r.responded} of {r.submitted}", axis=1,
    )
    data["tip"] = data.apply(
        lambda r: f"{r.source} — {r.responded} of {r.submitted} responded ({r.pct}%)",
        axis=1,
    )
    order = list(data["source"])
    y = alt.Y("source:N", sort=order, title=None,
              axis=alt.Axis(grid=False, labelColor=TOKENS["text"], labelFontSize=12,
                            labelPadding=10))
    base = alt.Chart(data).encode(y=y)
    track = base.mark_bar(height=12, color=TOKENS["surface_muted"], aria=False).encode(
        x=alt.X("full:Q", axis=None, scale=alt.Scale(domain=[0, 140])),
    ).transform_calculate(full="100")
    bars = base.mark_bar(height=12, cornerRadiusEnd=2, color=TOKENS["olive"]).encode(
        x=alt.X("pct:Q", axis=None, scale=alt.Scale(domain=[0, 140])),
        tooltip=alt.Tooltip("tip:N"),
        description=alt.Description("tip:N"),
    )
    labels = base.mark_text(align="left", dx=8, color=TOKENS["muted"], aria=False).encode(
        x=alt.X("full:Q", scale=alt.Scale(domain=[0, 140])),
        text="label:N",
    ).transform_calculate(full="100")
    return (track + bars + labels).properties(height=max(len(data), 1) * 30)


def score_history_chart(scores: pd.DataFrame) -> alt.Chart:
    """Resume match score per scan (line with points), 0–100 scale.

    Scans are spaced evenly (one step per scan) rather than on a time axis,
    so several scans on the same day stay readable. Labels read "Nov 16",
    with "· 2", "· 3" added when a day has more than one scan.
    *scores* has columns scanned_at (datetime-like) and overall_score.
    """
    data = scores[["scanned_at", "overall_score"]].copy()
    data["scanned_at"] = pd.to_datetime(data["scanned_at"])
    data = data.sort_values("scanned_at").reset_index(drop=True)
    days = data["scanned_at"].map(_fmt_day)
    nth = days.groupby(days).cumcount() + 1
    multi = days.map(days.value_counts()) > 1
    data["scan"] = [f"{d} · {n}" if m else d for d, n, m in zip(days, nth, multi)]
    data["score"] = data["overall_score"].round().astype(int)
    data["tip"] = data.apply(lambda r: f"{r.scan} — score {r.score}", axis=1)
    order = list(data["scan"])
    enc = dict(
        x=alt.X("scan:N", sort=order, title=None, scale=alt.Scale(padding=0.5)),
        y=alt.Y("score:Q", title=None, scale=alt.Scale(domain=[0, 100])),
    )
    line = alt.Chart(data).mark_line().encode(**enc)
    pts = alt.Chart(data).mark_point().encode(
        **enc, tooltip=alt.Tooltip("tip:N"), description=alt.Description("tip:N"),
    )
    return (line + pts).properties(height=180)
