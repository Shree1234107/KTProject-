"""Dashboard metrics computed from the applications DataFrame."""
import pandas as pd

from .db import STATUSES

# Statuses meaning the company responded beyond a plain rejection-less silence
ADVANCED = {"OA/Screen", "Interview", "Offer"}
SUBMITTED = set(STATUSES) - {"Wishlist"}


def summary(df):
    submitted = df[df["status"].isin(SUBMITTED)]
    n = len(submitted)
    advanced = submitted["status"].isin(ADVANCED | {"Rejected"}).sum()  # got any response
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
