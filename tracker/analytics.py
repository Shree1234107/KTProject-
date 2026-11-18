"""Dashboard metrics computed from the applications DataFrame."""
import pandas as pd

from .db import STATUSES, STAGE_TYPES

ADVANCED = {"OA/Screen", "Interview", "Offer"}
SUBMITTED = set(STATUSES) - {"Wishlist"}


# ---------------------------------------------------------------------------
# Internal helpers — stages-aware responded / interviewed masks
# ---------------------------------------------------------------------------

def _stage_app_ids(stages_df) -> set:
    """Return the set of application_ids that have at least one logged stage."""
    if stages_df is None or stages_df.empty:
        return set()
    return set(stages_df["application_id"].unique())


def _responded_mask(submitted: pd.DataFrame, stage_app_ids: set) -> pd.Series:
    """True for submitted rows that have responded (by status or by any logged stage)."""
    by_status = submitted["status"].isin(ADVANCED | {"Rejected"})
    if stage_app_ids:
        return by_status | submitted["id"].isin(stage_app_ids)
    return by_status


def _interviewed_mask(submitted: pd.DataFrame, stage_app_ids: set) -> pd.Series:
    """True for submitted rows at interview level (by status or by any logged stage)."""
    by_status = submitted["status"].isin({"Interview", "Offer"})
    if stage_app_ids:
        return by_status | submitted["id"].isin(stage_app_ids)
    return by_status


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def summary(df, stages_df=None):
    stage_ids = _stage_app_ids(stages_df)
    submitted = df[df["status"].isin(SUBMITTED)]
    n = len(submitted)
    advanced    = int(_responded_mask(submitted, stage_ids).sum())
    interviewed = int(_interviewed_mask(submitted, stage_ids).sum())
    return {
        "total":          len(df),
        "submitted":      n,
        "response_rate":  (advanced    / n) if n else 0.0,
        "interview_rate": (interviewed / n) if n else 0.0,
        "offers":         int((df["status"] == "Offer").sum()),
        "active":         int(df["status"].isin({"Applied", "OA/Screen", "Interview"}).sum()),
    }


def status_counts(df):
    return df["status"].value_counts().reindex(STATUSES, fill_value=0)


def applications_per_week(df):
    d = df.dropna(subset=["date_applied"])
    if d.empty:
        return pd.Series(dtype=int)
    return d.set_index("date_applied").resample("W").size()


def weekly_counts(df: pd.DataFrame, today=None, weeks: int = 12) -> pd.DataFrame:
    """Submitted applications per Mon–Sun week for the last *weeks* weeks.

    Empty weeks are included as 0 so the chart has no gaps. Uses the same
    rule as the weekly goal (non-Wishlist rows with a date_applied).
    Returns columns ``week_start`` (Timestamp, Monday) and ``count`` (int).
    """
    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    this_mon = today_ts - pd.Timedelta(days=today_ts.day_of_week)
    starts = [this_mon - pd.Timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]

    d = df[df["status"].isin(SUBMITTED)].dropna(subset=["date_applied"])
    mondays = d["date_applied"] - pd.to_timedelta(d["date_applied"].dt.day_of_week, unit="D")
    per_week = mondays.dt.normalize().value_counts()
    counts = [int(per_week.get(w, 0)) for w in starts]
    return pd.DataFrame({"week_start": starts, "count": counts})


def response_by_source(df: pd.DataFrame, stages_df=None) -> pd.DataFrame:
    """Response rate per source among submitted applications, highest first.

    Uses the same "responded" rule as the KPI row. Returns columns
    ``source``, ``submitted``, ``responded``, ``rate`` (0–1 float).
    """
    cols = ["source", "submitted", "responded", "rate"]
    sub = df[df["status"].isin(SUBMITTED)]
    sub = sub[sub["source"].fillna("").str.strip() != ""]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub = sub.assign(_resp=_responded_mask(sub, _stage_app_ids(stages_df)))
    g = sub.groupby("source").agg(submitted=("id", "count"), responded=("_resp", "sum"))
    g["responded"] = g["responded"].astype(int)
    g["rate"] = g["responded"] / g["submitted"]
    g = g.reset_index().sort_values(["rate", "submitted"], ascending=[False, False])
    return g[cols].reset_index(drop=True)


def by_source(df):
    d = df[df["source"].str.strip() != ""]
    if d.empty:
        return pd.DataFrame(columns=["source", "applications", "advanced"])
    g = d.groupby("source").agg(
        applications=("id", "count"),
        advanced=("status", lambda s: s.isin(ADVANCED).sum()),
    )
    return g.sort_values("applications", ascending=False).reset_index()


def upcoming_deadlines(df, today=None, days=14):
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    d = df.dropna(subset=["deadline"])
    d = d[d["status"].isin({"Wishlist", "Applied"})]
    d = d[(d["deadline"] >= today) & (d["deadline"] <= today + pd.Timedelta(days=days))]
    return d.sort_values("deadline")[["company", "role", "deadline", "status"]]


def referral_comparison(df: pd.DataFrame, stages_df=None) -> dict:
    stage_ids = _stage_app_ids(stages_df)
    zero = {"count": 0, "submitted": 0, "response_rate": 0.0, "interview_rate": 0.0}
    if df.empty or "referral_name" not in df.columns:
        return {"referred": dict(zero), "cold": dict(zero)}

    referred_mask = df["referral_name"].fillna("").str.strip() != ""
    result = {}
    for label, mask in [("referred", referred_mask), ("cold", ~referred_mask)]:
        group = df[mask]
        submitted = group[group["status"].isin(SUBMITTED)]
        n = len(submitted)
        responded   = int(_responded_mask(submitted, stage_ids).sum())
        interviewed = int(_interviewed_mask(submitted, stage_ids).sum())
        result[label] = {
            "count":          len(group),
            "submitted":      n,
            "response_rate":  (responded   / n) if n else 0.0,
            "interview_rate": (interviewed / n) if n else 0.0,
        }
    return result


def reminders(df: pd.DataFrame, today=None) -> dict[str, pd.DataFrame]:
    """Group applications with a follow_up_date into overdue/due_today/upcoming.

    Skips Rejected and Withdrawn rows. Upcoming = within the next 14 days.
    Returns {"overdue": df, "due_today": df, "upcoming": df}.
    """
    empty = pd.DataFrame()
    if "follow_up_date" not in df.columns:
        return {"overdue": empty, "due_today": empty, "upcoming": empty}

    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    active = df[~df["status"].isin({"Rejected", "Withdrawn"})]
    active = active.dropna(subset=["follow_up_date"])

    overdue   = active[active["follow_up_date"] <  today_ts]
    due_today = active[active["follow_up_date"] == today_ts]
    upcoming  = active[
        (active["follow_up_date"] >  today_ts) &
        (active["follow_up_date"] <= today_ts + pd.Timedelta(days=14))
    ]
    return {"overdue": overdue, "due_today": due_today, "upcoming": upcoming}


def stale_applications(df: pd.DataFrame, today=None, days: int = 21) -> pd.DataFrame:
    """Return Applied rows with no reply after `days` days.

    Adds a `days_waiting` column (integer).
    """
    if "date_applied" not in df.columns:
        return pd.DataFrame()

    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    applied = df[df["status"] == "Applied"].dropna(subset=["date_applied"])
    cutoff = today_ts - pd.Timedelta(days=days)
    stale = applied[applied["date_applied"] <= cutoff].copy()
    stale["days_waiting"] = (today_ts - stale["date_applied"]).dt.days.astype(int)
    return stale.sort_values("days_waiting", ascending=False)


# ---------------------------------------------------------------------------
# Feature: Kanban board helpers
# ---------------------------------------------------------------------------

_PIPELINE = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer"]


def next_status(status: str) -> "str | None":
    """Next stage in the pipeline, or None if already at Offer or not in pipeline."""
    try:
        idx = _PIPELINE.index(status)
        return _PIPELINE[idx + 1] if idx < len(_PIPELINE) - 1 else None
    except ValueError:
        return None


def prev_status(status: str) -> "str | None":
    """Previous stage in the pipeline, or None if at Wishlist or not in pipeline."""
    try:
        idx = _PIPELINE.index(status)
        return _PIPELINE[idx - 1] if idx > 0 else None
    except ValueError:
        return None


PIPELINE = _PIPELINE


def stage_timeline(history: pd.DataFrame, app_id: int, status: str,
                   date_applied=None) -> list[tuple[str, "pd.Timestamp | None"]]:
    """Ordered (status, date) moves for one application.

    Uses recorded status changes when there are any. Older applications
    (saved before history existed) fall back to a single entry: the current
    status, dated by date_applied when known.
    """
    rows = history[history["application_id"] == int(app_id)] if not history.empty else history
    if rows is None or rows.empty:
        d = date_applied if date_applied is not None and pd.notna(date_applied) else None
        return [(status, d)]
    out = [(r.status, r.changed_on) for r in rows.itertuples()]
    if out[-1][0] != status:  # status was changed outside the tracked path
        out.append((status, None))
    return out


def days_in_stage(timeline, today=None) -> "int | None":
    """Days since the last move, or None when the date is unknown."""
    last = timeline[-1][1] if timeline else None
    if last is None or pd.isna(last):
        return None
    today = pd.Timestamp(today or pd.Timestamp.today().date())
    return max(0, (today - pd.Timestamp(last).normalize()).days)


STALE_STATUSES = ("Applied", "OA/Screen", "Interview")


def is_stale(status: str, days: "int | None", threshold: int) -> bool:
    """An active job that hasn't moved in `threshold` days or more."""
    return status in STALE_STATUSES and days is not None and days >= threshold


# ---------------------------------------------------------------------------
# Feature: Application heatmap
# ---------------------------------------------------------------------------

def applications_per_day(df: pd.DataFrame, today=None, weeks: int = 26) -> dict:
    """Count submitted (non-Wishlist) applications per calendar day.

    Returns a ``{date: count}`` dict for the last *weeks* weeks ending on
    *today*. Dates with zero applications are absent from the dict.
    """
    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    start_ts = today_ts - pd.Timedelta(weeks=weeks)

    submitted = df[df["status"] != "Wishlist"].dropna(subset=["date_applied"])
    if submitted.empty:
        return {}

    in_win = submitted[
        (submitted["date_applied"] >= start_ts) &
        (submitted["date_applied"] <= today_ts)
    ]
    if in_win.empty:
        return {}

    counts = in_win["date_applied"].dt.normalize().value_counts()
    return {ts.date(): int(c) for ts, c in counts.items()}


# ---------------------------------------------------------------------------
# Feature: Funnel chart
# ---------------------------------------------------------------------------

def funnel(df: pd.DataFrame, stages_df=None) -> dict:
    """Compute pipeline funnel counts and step-conversion rates.

    Returns applied / responded / interviewed / offered counts plus
    ``pct_responded``, ``pct_interviewed``, ``pct_offered`` as fractions
    relative to *applied*.
    """
    stage_ids = _stage_app_ids(stages_df)
    submitted = df[df["status"].isin(SUBMITTED)]
    n = len(submitted)
    if n == 0:
        return {
            "applied": 0, "responded": 0, "interviewed": 0, "offered": 0,
            "pct_responded": 0.0, "pct_interviewed": 0.0, "pct_offered": 0.0,
            "pct_step_interviewed": 0.0, "pct_step_offered": 0.0,
        }
    responded   = int(_responded_mask(submitted, stage_ids).sum())
    interviewed = int(_interviewed_mask(submitted, stage_ids).sum())
    offered     = int((submitted["status"] == "Offer").sum())
    return {
        "applied":               n,
        "responded":             responded,
        "interviewed":           interviewed,
        "offered":               offered,
        "pct_responded":         responded   / n,
        "pct_interviewed":       interviewed / n,
        "pct_offered":           offered     / n,
        "pct_step_interviewed":  interviewed / responded  if responded   > 0 else 0.0,
        "pct_step_offered":      offered     / interviewed if interviewed > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Feature: Weekly goal and streak
# ---------------------------------------------------------------------------

def weekly_progress(df: pd.DataFrame, goal: int, today=None) -> dict:
    """Count non-Wishlist applications submitted in the current Mon-Sun week.

    Returns ``{"count": int, "goal": int, "met": bool}``.
    """
    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    week_start = today_ts - pd.Timedelta(days=today_ts.day_of_week)
    week_end   = week_start + pd.Timedelta(days=6)

    submitted = df[df["status"] != "Wishlist"].dropna(subset=["date_applied"])
    count = int(submitted[
        (submitted["date_applied"] >= week_start) &
        (submitted["date_applied"] <= week_end)
    ].shape[0])
    return {"count": count, "goal": goal, "met": count >= goal}


def goal_streak(df: pd.DataFrame, goal: int, today=None) -> dict:
    """Return current and longest streak of Mon-Sun weeks meeting *goal*.

    The current (incomplete) week is included once its count has reached
    the goal. Returns ``{"current": int, "longest": int}``.
    """
    today_ts = pd.Timestamp(today or pd.Timestamp.today().normalize())
    this_mon  = today_ts - pd.Timedelta(days=today_ts.day_of_week)

    submitted = df[df["status"] != "Wishlist"].dropna(subset=["date_applied"])
    if submitted.empty:
        return {"current": 0, "longest": 0}

    earliest     = submitted["date_applied"].min()
    earliest_mon = earliest - pd.Timedelta(days=earliest.day_of_week)

    def _week_met(w_start):
        w_end = w_start + pd.Timedelta(days=6)
        return int(submitted[
            (submitted["date_applied"] >= w_start) &
            (submitted["date_applied"] <= w_end)
        ].shape[0]) >= goal

    seq = []
    w = this_mon
    while w >= earliest_mon and len(seq) < 260:
        seq.append(_week_met(w))
        w -= pd.Timedelta(weeks=1)

    current = 0
    for met in seq:
        if met:
            current += 1
        else:
            break

    longest = run = 0
    for met in seq:
        if met:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    return {"current": current, "longest": longest}


# ---------------------------------------------------------------------------
# Feature: Period comparison (trend tiles)
# ---------------------------------------------------------------------------

def period_comparison(df: pd.DataFrame, today=None, days: int = 30, stages_df=None) -> dict:
    """Compare key metrics for the last *days* days vs the *days* days before.

    Returns::

        {
          "has_trend": bool,  # True only if both windows have data
          "current":  {total, response_rate, interview_rate, offers} | None,
          "previous": {total, response_rate, interview_rate, offers} | None,
        }
    """
    today_ts   = pd.Timestamp(today or pd.Timestamp.today().normalize())
    curr_start = today_ts - pd.Timedelta(days=days)
    prev_start = curr_start - pd.Timedelta(days=days)

    dated = df.dropna(subset=["date_applied"])

    curr_df = dated[dated["date_applied"] >= curr_start]
    prev_df = dated[
        (dated["date_applied"] >= prev_start) &
        (dated["date_applied"] <  curr_start)
    ]

    def _filter_stages(sdf):
        if stages_df is None or stages_df.empty or sdf.empty:
            return stages_df
        app_ids = set(sdf["id"])
        return stages_df[stages_df["application_id"].isin(app_ids)]

    def _m(sdf):
        s = summary(sdf, _filter_stages(sdf))
        return {
            "total":          s["total"],
            "response_rate":  s["response_rate"],
            "interview_rate": s["interview_rate"],
            "offers":         s["offers"],
        }

    _TREND_MIN = 5
    curr_sub = int(curr_df["status"].isin(SUBMITTED).sum()) if not curr_df.empty else 0
    prev_sub = int(prev_df["status"].isin(SUBMITTED).sum()) if not prev_df.empty else 0

    return {
        "has_trend": curr_sub >= _TREND_MIN and prev_sub >= _TREND_MIN,
        "current":   _m(curr_df) if not curr_df.empty else None,
        "previous":  _m(prev_df) if not prev_df.empty else None,
    }


# ---------------------------------------------------------------------------
# Feature: Interview stage pass rates
# ---------------------------------------------------------------------------

def stage_pass_rates(stages_df: pd.DataFrame) -> pd.DataFrame:
    """Per stage type: passed, failed, pending, pass_rate.

    pass_rate = Passed / (Passed + Failed). None when no decided outcomes.
    Returns a DataFrame with columns: stage, passed, failed, pending, pass_rate.
    Only returns rows for stage types that have at least one entry.
    """
    if stages_df is None or stages_df.empty:
        return pd.DataFrame(columns=["stage", "passed", "failed", "pending", "pass_rate"])

    rows = []
    for stage in STAGE_TYPES:
        sub = stages_df[stages_df["stage"] == stage]
        if sub.empty:
            continue
        passed  = int((sub["outcome"] == "Passed").sum())
        failed  = int((sub["outcome"] == "Failed").sum())
        pending = int(sub["outcome"].isin({"Scheduled", "Pending"}).sum())
        decided = passed + failed
        pass_rate = (passed / decided) if decided > 0 else None
        rows.append({
            "stage":     stage,
            "passed":    passed,
            "failed":    failed,
            "pending":   pending,
            "pass_rate": pass_rate,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Feature: Latest match scores per application
# ---------------------------------------------------------------------------

def latest_match_scores(scores_df: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent score scan per application_id.

    Returns one row per application, keeping all columns from the latest scan.
    """
    if scores_df is None or scores_df.empty:
        return pd.DataFrame(columns=["application_id", "overall_score"])
    return (
        scores_df
        .sort_values("scanned_at", ascending=False)
        .drop_duplicates(subset=["application_id"])
        .reset_index(drop=True)
    )


RESPONSE_STATUSES = {"OA/Screen", "Interview", "Offer", "Rejected"}


def first_response_days(apps: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Days from applying to the first reply (a screen, interview, offer or rejection).

    Returns columns id, source, days — one row per job that has heard back.
    """
    cols = ["id", "source", "days"]
    if apps.empty or history.empty:
        return pd.DataFrame(columns=cols)
    h = history[history["status"].isin(RESPONSE_STATUSES)].copy()
    h["on"] = pd.to_datetime(h["changed_on"], errors="coerce")
    first = h.dropna(subset=["on"]).groupby("application_id")["on"].min()
    a = apps.dropna(subset=["date_applied"]).copy()
    a["applied"] = pd.to_datetime(a["date_applied"], errors="coerce")
    a = a[a["id"].isin(first.index)]
    a["days"] = (a["id"].map(first) - a["applied"]).dt.days
    a = a[a["days"] >= 0]
    a["source"] = a["source"].fillna("").replace("", "No source")
    return a[cols].reset_index(drop=True)
