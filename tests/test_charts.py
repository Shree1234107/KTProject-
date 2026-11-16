"""Tests for tracker.charts: data shaping and friendly tooltips."""
import json

import pandas as pd

from tracker import charts
from tracker.db import STATUSES


def _spec(chart):
    return json.loads(chart.to_json())


def _datasets(spec):
    return [row for rows in spec.get("datasets", {}).values() for row in rows]


def test_pipeline_has_all_stages_in_order_with_tips():
    spec = _spec(charts.pipeline_chart(pd.Series({"Applied": 6, "Offer": 1})))
    rows = _datasets(spec)
    stages = [r["stage"] for r in rows if "stage" in r][: len(STATUSES)]
    assert stages == STATUSES
    tips = {r["tip"] for r in rows if "tip" in r}
    assert "Applied — 6 applications" in tips
    assert "Offer — 1 application" in tips
    assert "Wishlist — 0 applications" in tips


def test_weekly_chart_tooltips_and_goal():
    wc = pd.DataFrame({
        "week_start": pd.date_range("2026-08-31", periods=12, freq="W-MON"),
        "count": [0, 1, 2, 0, 3, 1, 0, 0, 2, 1, 0, 0],
    })
    spec = _spec(charts.weekly_chart(wc, 10))
    tips = {r.get("tip") for r in _datasets(spec)}
    assert "Week of Nov 2 — 1 application" in tips
    assert "Week of Nov 9 — 0 applications" in tips
    assert "Week of Sep 14 — 2 applications" in tips
    assert "Weekly goal — 10" in tips
    assert "date_applied" not in json.dumps(spec)


def test_score_history_same_day_scans_get_numbered():
    scores = pd.DataFrame({
        "scanned_at": ["2026-11-16 10:00:00", "2026-11-16 10:00:05"],
        "overall_score": [65, 72],
    })
    tips = [r["tip"] for r in _datasets(_spec(charts.score_history_chart(scores)))]
    assert tips == ["Nov 16 · 1 — score 65", "Nov 16 · 2 — score 72"]


def test_response_rate_chart_labels():
    rbs = pd.DataFrame({"source": ["Referral"], "submitted": [4], "responded": [3], "rate": [0.75]})
    rows = _datasets(_spec(charts.response_rate_chart(rbs)))
    assert rows[0]["label"] == "75%  ·  3 of 4"
    assert rows[0]["tip"] == "Referral — 3 of 4 responded (75%)"
