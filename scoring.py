"""Rule-based scores for Growth (primary), Exchange, and Absenteeism."""

from __future__ import annotations

import pandas as pd

GROWTH_KEYWORDS = [
    "built",
    "learned",
    "improved",
    "migrated",
    "automated",
    "documented",
    "optimized",
    "designed",
    "proposed",
    "mentored",
    "trained",
    "researched",
    "shipped",
    "launched",
    "refactored",
    "new",
    "first time",
    "experiment",
    "initiative",
]

EXCHANGE_KEYWORDS = [
    "shared",
    "presented",
    "demo",
    "documented",
    "paired",
    "pairing",
    "reviewed",
    "slack",
    "meeting",
    "discussed",
    "collaborat",
    "team",
    "colleague",
    "tenacious",
    "feedback",
    "knowledge",
    "wiki",
    "doc",
]

ABSENTEEISM_KEYWORDS = [
    "sick",
    "ill",
    "wfh",
    "work from home",
    "late",
    "absent",
    "couldn't work",
    "could not work",
    "day off",
    "leave",
    "covering for",
    "cover for",
    "exhausted",
    "burnout",
    "overwhelmed",
]

STAGNATION_PHRASES = [
    "did my job",
    "routine week",
    "nothing special",
    "same as usual",
    "handled tickets",
    "closed tickets",
    "updated ticket",
]


def _text_blob(row: pd.Series) -> str:
    parts = [
        row.get("key_achievements", ""),
        row.get("challenges", ""),
        row.get("other_highlights", ""),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def score_growth(row: pd.Series, prior_achievements: list[str] | None = None) -> float:
    """0–100. Higher = more growth signals."""
    text = _text_blob(row)
    achievements = str(row.get("key_achievements", "")).lower()
    score = 0.0

    score += min(30, sum(5 for kw in GROWTH_KEYWORDS if kw in achievements))
    score += min(15, len(achievements.split()) // 8 * 5)

    completed = row.get("tickets_completed")
    expected = row.get("tickets_expected")
    if pd.notna(completed) and pd.notna(expected) and expected > 0:
        ratio = float(completed) / float(expected)
        if ratio >= 1.0:
            score += 15
        elif ratio >= 0.85:
            score += 8

    qa = row.get("qa_first_pass_pct")
    if pd.notna(qa):
        if qa >= 90:
            score += 10
        elif qa >= 75:
            score += 5

    rating = row.get("overall_rating")
    if pd.notna(rating):
        score += min(15, float(rating) * 3)

    highlights = str(row.get("other_highlights", "")).strip()
    if len(highlights) > 20:
        score += 10

    for phrase in STAGNATION_PHRASES:
        if phrase in achievements and len(achievements) < 120:
            score -= 10
            break

    if prior_achievements:
        for old in prior_achievements[-3:]:
            if old and achievements.strip() == old.strip():
                score -= 15
                break
            if old and len(old) > 30 and old in achievements:
                score -= 10
                break

    return float(max(0, min(100, score)))


def score_exchange(row: pd.Series) -> float:
    """0–100. Higher = more openness / sharing."""
    text = _text_blob(row)
    score = min(50, sum(8 for kw in EXCHANGE_KEYWORDS if kw in text))
    highlights = str(row.get("other_highlights", "")).strip()
    if len(highlights) > 30:
        score += 15
    if "tenacious" in text:
        score += 10
    achievements = str(row.get("key_achievements", ""))
    if len(achievements) < 40:
        score -= 15
    return float(max(0, min(100, score)))


def score_absenteeism(row: pd.Series) -> float:
    """0–100. Higher = more absenteeism / availability concern."""
    text = _text_blob(row)
    score = min(60, sum(12 for kw in ABSENTEEISM_KEYWORDS if kw in text))
    rating = row.get("overall_rating")
    if pd.notna(rating) and rating <= 2:
        score += 15
    met = str(row.get("met_expectations", "")).lower()
    if met in ("no", "partially", "partial"):
        score += 10
    return float(max(0, min(100, score)))


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add growth, exchange, absenteeism scores and flags per row."""
    if "email" not in df.columns:
        raise ValueError(
            "No 'email' column after loading. Expected a column like 'Email address'. "
            f"Got: {list(df.columns)}"
        )
    sort_cols = [c for c in ("email", "timestamp") if c in df.columns]
    df = df.sort_values(sort_cols).copy()
    prior_by_email: dict[str, list[str]] = {}

    growth_scores = []
    exchange_scores = []
    absenteeism_scores = []
    flags = []

    for _, row in df.iterrows():
        email = row.get("email", "")
        prior = prior_by_email.get(email, [])
        g = score_growth(row, prior)
        e = score_exchange(row)
        a = score_absenteeism(row)
        growth_scores.append(g)
        exchange_scores.append(e)
        absenteeism_scores.append(a)

        row_flags = []
        if g < 40:
            row_flags.append("low_growth")
        if e < 35:
            row_flags.append("low_exchange")
        if a >= 40:
            row_flags.append("availability_concern")
        if pd.notna(row.get("overall_rating")) and row["overall_rating"] <= 3:
            row_flags.append("low_rating")
        flags.append(row_flags)

        ach = str(row.get("key_achievements", ""))
        prior_by_email.setdefault(email, []).append(ach)

    df["growth_score"] = growth_scores
    df["exchange_score"] = exchange_scores
    df["absenteeism_score"] = absenteeism_scores
    df["flags"] = flags
    df["growth_tier"] = pd.cut(
        df["growth_score"],
        bins=[-1, 40, 65, 100],
        labels=["Needs attention", "Developing", "Strong growth"],
    )
    return df


def latest_per_person(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "email" not in df.columns:
        return df
    return (
        df.sort_values("timestamp")
        .groupby("email", as_index=False)
        .tail(1)
        .sort_values("growth_score", ascending=False)
    )
