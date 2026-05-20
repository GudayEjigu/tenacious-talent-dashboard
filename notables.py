"""Display helpers for weekly check-in rows (form fields only — no custom scores)."""

from __future__ import annotations

import pandas as pd

WEEKLY_FIELDS: tuple[tuple[str, str], ...] = (
    ("timestamp", "Submitted"),
    ("key_achievements", "Key achievements"),
    ("tickets_completed", "Tickets completed (QA / Done)"),
    ("tickets_expected", "Expected tickets"),
    ("qa_first_pass_pct", "QA passed first attempt (%)"),
    ("challenges", "Challenges"),
    ("met_expectations", "Met employer expectations"),
    ("overall_rating", "Self-rating (1–5)"),
    ("other_highlights", "Other highlights"),
)

# label, emoji, streamlit message fn name
WEEK_LEVELS: dict[str, tuple[str, str]] = {
    "strong": ("Strong week", "🟢"),
    "good": ("Good week", "🟡"),
    "mixed": ("Mixed week", "🟠"),
    "tough": ("Tough week", "🔴"),
    "unknown": ("No score", "⚪"),
}


def format_week_label(row: pd.Series) -> str:
    ts = row.get("timestamp")
    if pd.notna(ts):
        return pd.Timestamp(ts).strftime("%d %b %Y")
    week = row.get("week")
    if pd.notna(week) and str(week).strip():
        return str(week)
    return "Unknown date"


def week_level(row: pd.Series) -> str:
    """
    Simple week band from their own form answers (rating + expectations + tickets).
    Returns key in WEEK_LEVELS.
    """
    rating = row.get("overall_rating")
    met = str(row.get("met_expectations", "")).strip().lower()
    completed = row.get("tickets_completed")
    expected = row.get("tickets_expected")

    below_target = False
    if pd.notna(completed) and pd.notna(expected) and float(expected) > 0:
        below_target = float(completed) / float(expected) < 0.7

    if pd.isna(rating):
        if met in ("no", "partially", "partial"):
            return "tough"
        if below_target:
            return "mixed"
        return "unknown"

    r = float(rating)
    if met == "no" or r <= 2:
        return "tough"
    if met in ("partially", "partial") or r == 3 or below_target:
        return "mixed"
    if r >= 5 and met in ("yes", "y", ""):
        return "strong"
    if r >= 4:
        return "good"
    return "mixed"


def person_weeks(df: pd.DataFrame, email: str) -> pd.DataFrame:
    """All submissions for one person, newest week first."""
    subset = df[df["email"] == email].copy()
    if "timestamp" in subset.columns:
        return subset.sort_values("timestamp", ascending=False)
    if "week" in subset.columns:
        return subset.sort_values("week", ascending=False)
    return subset


def person_summary(weeks_df: pd.DataFrame) -> dict:
    """Aggregate from their submitted ratings only."""
    ratings = weeks_df["overall_rating"].dropna() if "overall_rating" in weeks_df.columns else pd.Series(dtype=float)
    if ratings.empty:
        return {"avg_rating": None, "weeks_rated": 0, "strong": 0, "good": 0, "mixed": 0, "tough": 0}
    levels = [week_level(weeks_df.loc[i]) for i in weeks_df.index]
    return {
        "avg_rating": float(ratings.mean()),
        "weeks_rated": int(len(ratings)),
        "strong": levels.count("strong"),
        "good": levels.count("good"),
        "mixed": levels.count("mixed"),
        "tough": levels.count("tough"),
    }
