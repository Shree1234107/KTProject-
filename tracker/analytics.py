"""Dashboard metrics computed from the applications DataFrame."""
import pandas as pd

from .db import STATUSES

ADVANCED = {"OA/Screen", "Interview", "Offer"}
SUBMITTED = set(STATUSES) - {"Wishlist"}


def summary(df):
    submitted = df[df["status"].isin(SUBMITTED)]
    n = len(submitted)
    advanced = submitted["status"].isin(ADVANCED | {"Rejected"}).sum()
    return {
        "total": len(df),
        "submitted": n,
        "response_rate": (advanced / n) if n else 0.0,
        "interview_rate": (submitted["status"].isin({"Interview", "Offer"}).sum() / n) if n else 0.0,
        "offers": int((df["status"] == "Offer").sum()),
        "active": int(df["status"].isin({"Applied", "OA/Screen", "Interview"}).sum()),
    }


def status_counts(df):
    return df["status"].value_counts().reindex(STATUSES, fill_value=0)


def applications_per_week(df):
    d = df.dropna(subset=["date_applied"])
    if d.empty:
        return pd.Series(dtype=int)
    return d.set_index("date_applied").resample("W").size()


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


def referral_comparison(df: pd.DataFrame) -> dict:
    zero = {"count": 0, "submitted": 0, "response_rate": 0.0, "interview_rate": 0.0}
    if df.empty or "referral_name" not in df.columns:
        return {"referred": dict(zero), "cold": dict(zero)}

    referred_mask = df["referral_name"].fillna("").str.strip() != ""
    result = {}
    for label, mask in [("referred", referred_mask), ("cold", ~referred_mask)]:
        group = df[mask]
        submitted = group[group["status"].isin(SUBMITTED)]
        n = len(submitted)
        responded = submitted["status"].isin(ADVANCED | {"Rejected"}).sum()
        interviewed = submitted["status"].isin({"Interview", "Offer"}).sum()
        result[label] = {
            "count": len(group),
            "submitted": n,
            "response_rate": (responded / n) if n else 0.0,
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
