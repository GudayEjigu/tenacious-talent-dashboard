"""Simple v1 checks for weekly Telegram bot submissions — easy to scan."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# --- thresholds (tune in one place) ---
MIN_ACHIEVEMENT_CHARS = 80
TICKET_TARGET_RATIO = 0.80
MIN_QA_PASS_PCT = 80
MIN_SELF_RATING = 3
GENERIC_PHRASES = (
    "handled tickets",
    "closed tickets",
    "updated tickets",
    "routine week",
    "did my job",
    "nothing special",
    "same as usual",
)


@dataclass
class Check:
    """One line on the weekly checklist."""
    status: str  # ok | warn | watch
    label: str
    detail: str = ""


TALENT_ROSTER = {}


def display_name(email: str) -> str:
    """Talent name from roster, or formatted local-part as fallback."""
    if not email:
        return "Unknown"
    e_clean = str(email).strip().lower()
    if e_clean in TALENT_ROSTER:
        return TALENT_ROSTER[e_clean]["name"]
    if "@" not in e_clean:
        return e_clean.replace(".", " ").replace("_", " ").strip().title()
    local = e_clean.split("@", 1)[0]
    return local.replace(".", " ").replace("_", " ").strip().title()


def submission_timing(row: pd.Series) -> Check:
    ts = row.get("timestamp")
    if pd.isna(ts):
        return Check("watch", "Submitted", "No timestamp recorded")
    t = pd.Timestamp(ts)
    dow, hour = t.dayofweek, t.hour  # Mon=0 … Sun=6
    # On time: Sunday (6) or Monday (0) before noon
    if dow == 6 or (dow == 0 and hour < 12):
        return Check("ok", "Submitted on time", t.strftime("%a %d %b, %H:%M"))
    if dow == 0:
        return Check("warn", "Submitted late (Monday afternoon+)", t.strftime("%a %d %b, %H:%M"))
    return Check("warn", "Submitted late (after Monday)", t.strftime("%a %d %b, %H:%M"))


def _pct(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def week_checks(row: pd.Series, prior_row: pd.Series | None = None) -> list[Check]:
    checks: list[Check] = []

    achievements = str(row.get("key_achievements", "") or "").strip()
    if len(achievements) < MIN_ACHIEVEMENT_CHARS:
        checks.append(
            Check(
                "warn",
                "Achievements too short",
                f"{len(achievements)} chars — ask for more detail",
            )
        )
    else:
        checks.append(Check("ok", "Achievements length", f"{len(achievements)} chars"))

    completed = _pct(row.get("tickets_completed"))
    expected = _pct(row.get("tickets_expected"))
    if completed is not None and expected is not None and expected > 0:
        ratio = completed / expected
        if ratio >= TICKET_TARGET_RATIO:
            checks.append(
                Check("ok", "Tickets done vs expected", f"{int(completed)} / {int(expected)} ({ratio:.0%})")
            )
        else:
            checks.append(
                Check(
                    "warn",
                    "Tickets below 80% of expected",
                    f"{int(completed)} / {int(expected)} ({ratio:.0%}) — target is 80%+",
                )
            )
    else:
        checks.append(Check("watch", "Tickets", "Missing completed or expected count"))

    qa = _pct(row.get("qa_first_pass_pct"))
    if qa is not None:
        if qa >= MIN_QA_PASS_PCT:
            checks.append(Check("ok", "QA first-pass rate", f"{qa:.0f}%"))
        else:
            checks.append(Check("warn", "QA first-pass below 80%", f"{qa:.0f}%"))
    else:
        checks.append(Check("watch", "QA first-pass rate", "Not filled in"))

    challenges = str(row.get("challenges", "") or "").strip()
    checks.append(
        Check(
            "watch",
            "Challenges — read this",
            challenges if challenges else "(empty)",
        )
    )

    met = str(row.get("met_expectations", "") or "").strip().lower()
    if met in ("yes", "y"):
        checks.append(Check("ok", "Met expectations", "Yes"))
    elif met in ("partially", "partial"):
        checks.append(Check("warn", "Met expectations", "Partially — follow up"))
    elif met in ("no", "n"):
        checks.append(Check("warn", "Met expectations", "No — misaligned with Tenacious"))
    else:
        checks.append(Check("watch", "Met expectations", met or "Not answered"))

    rating = _pct(row.get("overall_rating"))
    if rating is not None:
        if rating >= MIN_SELF_RATING:
            checks.append(Check("ok", "Self-rating", f"{rating:.0f} / 5"))
        else:
            checks.append(Check("warn", "Self-rating below average", f"{rating:.0f} / 5"))
    else:
        checks.append(Check("watch", "Self-rating", "Not filled in"))

    highlights = str(row.get("other_highlights", "") or "").strip()
    if highlights:
        checks.append(Check("ok", "Extra highlights", "They added optional input"))
    else:
        checks.append(Check("watch", "Extra highlights", "None this week"))

    upload = str(row.get("upload", "") or "").strip()
    if upload and upload.lower() not in ("nan", "none"):
        checks.append(Check("ok", "Upload", "File or link provided"))
    else:
        checks.append(Check("watch", "Upload", "None"))

    # Generic / repetitive achievements
    ach_lower = achievements.lower()
    if any(p in ach_lower for p in GENERIC_PHRASES):
        checks.append(Check("warn", "Achievements look generic", "Very similar week-to-week language"))
    if prior_row is not None:
        prior_ach = str(prior_row.get("key_achievements", "") or "").strip().lower()
        if prior_ach and prior_ach == ach_lower and len(prior_ach) > 30:
            checks.append(Check("warn", "Same as last week", "Achievements text unchanged"))

    return checks


def ticket_gap_ratio(row: pd.Series) -> float | None:
    completed = _pct(row.get("tickets_completed"))
    expected = _pct(row.get("tickets_expected"))
    if completed is None or expected is None or expected <= 0:
        return None
    return max(0.0, (expected - completed) / expected)


def gap_widening(weeks_df: pd.DataFrame) -> Check | None:
    """Flag if expected-vs-actual gap is growing over recent weeks."""
    if len(weeks_df) < 2:
        return None
    chrono = weeks_df.sort_values("timestamp" if "timestamp" in weeks_df.columns else "week")
    gaps = [ticket_gap_ratio(chrono.loc[i]) for i in chrono.index]
    gaps = [g for g in gaps if g is not None]
    if len(gaps) < 2:
        return None
    if gaps[-1] > gaps[0] + 0.15:
        return Check(
            "warn",
            "Ticket gap widening",
            f"Shortfall was {gaps[0]:.0%} → now {gaps[-1]:.0%} of expected",
        )
    return Check("ok", "Ticket gap stable", f"Latest shortfall {gaps[-1]:.0%} of expected")


def person_summary_checks(weeks_df: pd.DataFrame) -> list[Check]:
    """Cross-week summary for the talent header."""
    out: list[Check] = []
    if weeks_df.empty:
        return out

    gap = gap_widening(weeks_df)
    if gap:
        out.append(gap)

    qa_col = weeks_df["qa_first_pass_pct"].dropna() if "qa_first_pass_pct" in weeks_df.columns else pd.Series()
    if len(qa_col) > 0:
        below = int((qa_col < MIN_QA_PASS_PCT).sum())
        if below:
            out.append(
                Check("warn", "QA below 80%", f"{below} of {len(qa_col)} week(s) under target")
            )
        else:
            out.append(Check("ok", "QA first-pass", f"All {len(qa_col)} week(s) at 80%+"))

    return out


def format_week_label(row: pd.Series) -> str:
    ts = row.get("timestamp")
    if pd.notna(ts):
        return pd.Timestamp(ts).strftime("%d %b %Y")
    week = row.get("week")
    if pd.notna(week) and str(week).strip():
        return str(week)
    return "Unknown week"


def person_weeks(df: pd.DataFrame, email: str) -> pd.DataFrame:
    subset = df[df["email"] == email].copy()
    if "timestamp" in subset.columns:
        return subset.sort_values("timestamp", ascending=False)
    if "week" in subset.columns:
        return subset.sort_values("week", ascending=False)
    return subset
