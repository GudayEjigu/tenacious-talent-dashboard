"""Transformation snapshot helpers for Telegram-to-growth evidence pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


SIGNAL_TAGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("win", ("completed", "done", "finished", "resolved", "delivered", "shipped", "approved", "achieved", "closed")),
    ("blocker", ("block", "blocked", "waiting", "stuck", "dependency", "delay", "issue", "challenge", "problem")),
    ("learning", ("learn", "learned", "studied", "researched", "understood", "new", "improved", "figured out")),
    ("risk", ("risk", "late", "miss", "failed", "unclear", "concern", "escalat", "deadline", "scope")),
    ("ownership signal", ("proposed", "suggested", "decided", "followed up", "took", "owned", "planned", "next step", "monitor")),
)

GROWTH_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Communication", ("client", "sent", "shared", "communicat", "update", "meeting", "sync", "reported", "explained")),
    ("Ownership", ("proposed", "suggested", "followed up", "owned", "took", "next step", "monitor", "decided")),
    ("Execution", ("completed", "done", "fixed", "resolved", "implemented", "built", "delivered", "tested", "qa")),
    ("Client Understanding", ("client", "requirement", "expectation", "business", "user", "customer", "impact")),
    ("Problem-Solving", ("debug", "investigat", "root cause", "figured", "solved", "tested", "analyzed", "issue")),
    ("Consistency", ("weekly", "continued", "maintained", "follow", "regular", "on time", "completed")),
    ("Professionalism", ("documented", "clear", "review", "quality", "responsible", "support", "handover")),
)

SCORING_WEIGHTS: tuple[dict[str, Any], ...] = (
    {
        "group": "Signal tags",
        "metric": "Win",
        "points": 8,
        "description": "The update shows a completed result, shipped work, approval, or resolved item.",
    },
    {
        "group": "Signal tags",
        "metric": "Blocker",
        "points": 6,
        "description": "The talent names a blocker, dependency, issue, or delivery constraint.",
    },
    {
        "group": "Signal tags",
        "metric": "Learning",
        "points": 8,
        "description": "The talent explains what they learned or how their capability improved.",
    },
    {
        "group": "Signal tags",
        "metric": "Risk",
        "points": 6,
        "description": "The update identifies risk, uncertainty, escalation, deadline pressure, or scope concern.",
    },
    {
        "group": "Signal tags",
        "metric": "Ownership Signal",
        "points": 12,
        "description": "The talent proposes a next step, follows up, makes a decision, or drives the issue forward.",
    },
    {
        "group": "Growth categories",
        "metric": "Communication",
        "points": 7,
        "description": "Evidence shows clear update-sharing with client, team, or manager.",
    },
    {
        "group": "Growth categories",
        "metric": "Ownership",
        "points": 9,
        "description": "Evidence shows accountability, follow-through, decision-making, or proactive action.",
    },
    {
        "group": "Growth categories",
        "metric": "Execution",
        "points": 8,
        "description": "Evidence shows implementation, delivery, testing, fixing, or task completion.",
    },
    {
        "group": "Growth categories",
        "metric": "Client Understanding",
        "points": 7,
        "description": "Evidence connects the work to client need, expectation, business context, or user impact.",
    },
    {
        "group": "Growth categories",
        "metric": "Problem-Solving",
        "points": 7,
        "description": "Evidence shows diagnosis, investigation, debugging, analysis, or solution choice.",
    },
    {
        "group": "Growth categories",
        "metric": "Consistency",
        "points": 4,
        "description": "Evidence shows steady weekly follow-through or continued progress.",
    },
    {
        "group": "Growth categories",
        "metric": "Professionalism",
        "points": 3,
        "description": "Evidence shows documentation, review discipline, handover, quality, or responsible conduct.",
    },
    {
        "group": "Evidence quality",
        "metric": "Achievement Detail",
        "points": 5,
        "description": "The raw achievement answer is specific enough to evaluate.",
    },
    {
        "group": "Evidence quality",
        "metric": "Evidence Strength",
        "points": 5,
        "description": "The writing contains direct proof rather than vague statements.",
    },
    {
        "group": "Evidence quality",
        "metric": "Extra Context / Artifact",
        "points": 5,
        "description": "The talent adds optional context, highlights, upload, artifact, or extra proof.",
    },
)


@dataclass(frozen=True)
class MetricState:
    label: str
    selected: bool
    value: str = ""
    detail: str = ""


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none"}:
        return ""
    return text


def email_identity(email: str) -> str:
    """Return the local-part identity, with common domains removed."""
    cleaned = clean_text(email).lower()
    return cleaned.split("@", 1)[0] if "@" in cleaned else cleaned


def slug(value: str, fallback: str = "unknown") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", clean_text(value).lower()).strip("-")
    return cleaned or fallback


def talent_id(email: str, name: str) -> str:
    return f"TAL-{slug(email_identity(email) or name).upper()}"


def client_id(client: str) -> str:
    return f"CL-{slug(client).upper()}"


def project_id(client: str, week: str) -> str:
    week_part = slug(str(week).split("/", 1)[0] if week else "")
    return f"PRJ-{slug(client).upper()}-{week_part.upper()}"


def format_submission_day(timestamp: Any) -> str:
    if timestamp is None or pd.isna(timestamp):
        return "No timestamp"
    ts = pd.Timestamp(timestamp)
    # User requested a day-name format like "Tues 12 May".
    day_name = {
        "Mon": "Mon",
        "Tue": "Tues",
        "Wed": "Wed",
        "Thu": "Thurs",
        "Fri": "Fri",
        "Sat": "Sat",
        "Sun": "Sun",
    }.get(ts.strftime("%a"), ts.strftime("%a"))
    return f"{day_name} {ts.day} {ts.strftime('%b')}"


def week_bounds(row: pd.Series) -> tuple[str, str]:
    week = clean_text(row.get("week"))
    if "/" in week:
        start, end = week.split("/", 1)
        return start.strip(), end.strip()
    ts = row.get("timestamp")
    if ts is not None and pd.notna(ts):
        start = pd.Timestamp(ts).to_period("W").start_time
        end = pd.Timestamp(ts).to_period("W").end_time
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    return "Unknown", "Unknown"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    haystack = text.lower()
    return any(keyword in haystack for keyword in keywords)


def _evidence_snippet(text: str, keywords: tuple[str, ...]) -> str:
    """Return a short source snippet explaining why a metric was selected."""
    source = clean_text(text)
    if not source:
        return ""
    lower = source.lower()
    for keyword in keywords:
        pos = lower.find(keyword)
        if pos >= 0:
            start = max(0, pos - 55)
            end = min(len(source), pos + len(keyword) + 85)
            snippet = source[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(source):
                snippet = snippet + "..."
            return snippet
    return source[:160] + ("..." if len(source) > 160 else "")


def combined_text(row: pd.Series) -> str:
    return " ".join(
        clean_text(row.get(col))
        for col in ("key_achievements", "challenges", "other_highlights")
        if clean_text(row.get(col))
    )


def detect_signal_metrics(row: pd.Series) -> list[MetricState]:
    text = combined_text(row)
    return [
        MetricState(label=label.title(), selected=_contains_any(text, keywords))
        for label, keywords in SIGNAL_TAGS
    ]


def detect_growth_category_metrics(row: pd.Series) -> list[MetricState]:
    text = combined_text(row)
    return [
        MetricState(label=label, selected=_contains_any(text, keywords))
        for label, keywords in GROWTH_CATEGORIES
    ]


def message_type(row: pd.Series) -> str:
    achievements = clean_text(row.get("key_achievements"))
    challenges = clean_text(row.get("challenges"))
    tags = [m.label.lower() for m in detect_signal_metrics(row) if m.selected]
    if "blocker" in tags or challenges:
        if achievements:
            return "Update + blocker"
        return "Blocker"
    if "learning" in tags:
        return "Learning"
    if "win" in tags:
        return "Win"
    return "Update" if achievements else "Missing update"


def score_from_growth(row: pd.Series) -> int:
    score = row.get("growth_score")
    if score is None or pd.isna(score):
        return 1
    score = float(score)
    if score >= 75:
        return 4
    if score >= 55:
        return 3
    if score >= 35:
        return 2
    return 1


def evidence_strength(row: pd.Series) -> str:
    achievements = clean_text(row.get("key_achievements"))
    active_tags = sum(1 for m in detect_signal_metrics(row) if m.selected)
    if len(achievements) >= 120 and active_tags >= 3:
        return "Strong"
    if len(achievements) >= 60 or active_tags >= 2:
        return "Moderate"
    return "Weak"


def confidence(row: pd.Series) -> str:
    strength = evidence_strength(row)
    if strength == "Strong":
        return "High"
    if strength == "Moderate":
        return "Medium"
    return "Low"


def score_rationale(row: pd.Series) -> str:
    selected = [m.label for m in detect_signal_metrics(row) if m.selected]
    if selected:
        return "Scored from visible evidence tags: " + ", ".join(selected) + "."
    return "Scored conservatively because the weekly evidence is limited or missing."


def delta_from_prior(row: pd.Series, prior: pd.Series | None) -> str:
    current = row.get("growth_score")
    previous = prior.get("growth_score") if prior is not None else None
    if current is None or pd.isna(current) or previous is None or pd.isna(previous):
        return "No prior comparison"
    delta = float(current) - float(previous)
    if abs(delta) < 0.5:
        return "Flat"
    return f"{delta:+.1f}"


def client_story(row: pd.Series, talent_name: str, client: str, prior: pd.Series | None = None) -> str:
    score = score_from_growth(row)
    delta = delta_from_prior(row, prior)
    selected = [m.label.lower() for m in detect_signal_metrics(row) if m.selected]
    client_label = client or "the client"
    if score >= 3 and selected:
        return (
            f"{talent_name}'s weekly evidence for {client_label} shows "
            f"{', '.join(selected[:3])}; growth movement is {delta}."
        )
    if clean_text(row.get("key_achievements")):
        return (
            f"{talent_name}'s update for {client_label} is captured, but the growth evidence "
            f"needs stronger detail before making a larger client-facing claim."
        )
    return f"No client-facing growth claim should be made for {talent_name} this week because no achievement evidence was captured."


def talent_scorecard(row: pd.Series) -> dict[str, str]:
    return {
        "growth_score": f"{float(row.get('growth_score')):.1f}" if pd.notna(row.get("growth_score")) else "N/A",
        "score_band": str(score_from_growth(row)),
        "confidence": confidence(row),
        "evidence_strength": evidence_strength(row),
    }


def score_to_100_breakdown(row: pd.Series) -> dict[str, Any]:
    """Explain why a growth score was earned and what remains to reach 100."""
    achievements = clean_text(row.get("key_achievements"))
    challenges = clean_text(row.get("challenges"))
    highlights = clean_text(row.get("other_highlights"))
    signal_metrics = detect_signal_metrics(row)
    category_metrics = detect_growth_category_metrics(row)
    active_signals = [m.label for m in signal_metrics if m.selected]
    missing_signals = [m.label for m in signal_metrics if not m.selected]
    active_categories = [m.label for m in category_metrics if m.selected]
    missing_categories = [m.label for m in category_metrics if not m.selected]

    score_value = row.get("growth_score")
    score_numeric = float(score_value) if score_value is not None and pd.notna(score_value) else 0.0
    remaining = max(0.0, 100.0 - score_numeric)

    earned: list[str] = []
    if achievements:
        earned.append(f"Raw achievement evidence was submitted ({len(achievements)} characters).")
    else:
        earned.append("No achievement evidence was submitted, so the report cannot prove weekly growth from the main Telegram answer.")

    if active_signals:
        earned.append("Detected signal tags: " + ", ".join(active_signals) + ".")
    else:
        earned.append("No strong signal tags were detected from the submitted text.")

    if active_categories:
        earned.append("Detected growth categories: " + ", ".join(active_categories) + ".")
    else:
        earned.append("No growth category was strongly evidenced by the submitted text.")

    if challenges:
        earned.append("Challenges/blockers were disclosed, which supports risk visibility.")
    if highlights:
        earned.append("Extra highlights were provided, adding optional context.")

    missing: list[str] = []
    if len(achievements) < 120:
        missing.append("More specific achievement detail: explain what changed, for whom, and what proof shows it worked.")
    if "Ownership Signal" in missing_signals:
        missing.append("Ownership signal: include the proposed next step, decision made, or follow-up action taken.")
    if "Learning" in missing_signals:
        missing.append("Learning signal: state what was learned and how it will improve future delivery.")
    if "Risk" in missing_signals and challenges:
        missing.append("Risk handling: explain mitigation, escalation, or what support is needed.")
    if "Communication" in missing_categories:
        missing.append("Communication evidence: mention who was updated and what message or decision was shared.")
    if "Client Understanding" in missing_categories:
        missing.append("Client understanding: connect the work to the client's goal, user impact, or business priority.")
    if "Professionalism" in missing_categories:
        missing.append("Professionalism evidence: include quality checks, documentation, handover, or review discipline.")
    if not highlights:
        missing.append("Optional highlight/context: add extra proof, artifact links, or a short reflection when meaningful.")

    if not missing:
        missing.append("To reach 100, keep the same evidence quality and add measurable client impact, artifacts, and clear next-step ownership.")

    next_actions = [
        "Write the weekly achievement as: outcome + evidence + client impact + next step.",
        "Name the blocker and the mitigation, not only the problem.",
        "Include at least one concrete proof point: ticket ID, shipped feature, client response, QA result, artifact, or metric.",
    ]

    if missing_categories:
        next_actions.append("Add evidence for missing categories: " + ", ".join(missing_categories[:4]) + ".")
    if missing_signals:
        next_actions.append("Add evidence for missing signals: " + ", ".join(missing_signals[:4]) + ".")

    return {
        "score_numeric": score_numeric,
        "remaining_to_100": remaining,
        "earned": earned,
        "missing": missing,
        "next_actions": next_actions,
        "active_signals": active_signals,
        "missing_signals": missing_signals,
        "active_categories": active_categories,
        "missing_categories": missing_categories,
    }


def weighted_metric_rows(row: pd.Series) -> list[dict[str, Any]]:
    """Return the visible 100-point map with earned/missing points."""
    text = combined_text(row)
    signal_states = {m.label: m.selected for m in detect_signal_metrics(row)}
    category_states = {m.label: m.selected for m in detect_growth_category_metrics(row)}
    signal_keywords = {label.title(): keywords for label, keywords in SIGNAL_TAGS}
    category_keywords = {label: keywords for label, keywords in GROWTH_CATEGORIES}
    achievements = clean_text(row.get("key_achievements"))
    highlights = clean_text(row.get("other_highlights"))
    upload = clean_text(row.get("upload"))
    strength = evidence_strength(row)

    rows: list[dict[str, Any]] = []
    for item in SCORING_WEIGHTS:
        metric = item["metric"]
        group = item["group"]
        if group == "Signal tags":
            selected = bool(signal_states.get(metric))
            evidence = _evidence_snippet(text, signal_keywords.get(metric, ())) if selected else f"Needs evidence of: {item['description']}"
        elif group == "Growth categories":
            selected = bool(category_states.get(metric))
            evidence = _evidence_snippet(text, category_keywords.get(metric, ())) if selected else f"Needs evidence of: {item['description']}"
        elif metric == "Achievement Detail":
            selected = len(achievements) >= 120
            evidence = (
                f"Achievement answer has {len(achievements)} characters."
                if selected
                else f"Achievement answer has {len(achievements)} characters; target is 120+."
            )
        elif metric == "Evidence Strength":
            selected = strength in {"Moderate", "Strong"}
            evidence = (
                f"Evidence strength is {strength} based on detail and detected signals."
                if selected
                else f"Evidence strength is {strength}; needs more direct proof."
            )
        elif metric == "Extra Context / Artifact":
            selected = bool(highlights or upload)
            if highlights:
                evidence = "Extra highlight: " + highlights[:180]
            elif upload:
                evidence = "Upload/artifact provided."
            else:
                evidence = "Needs optional context, highlight, upload, artifact, or extra proof."
        else:
            selected = False
            evidence = f"Needs evidence of: {item['description']}"

        points = int(item["points"])
        rows.append(
            {
                "group": group,
                "metric": metric,
                "points": points,
                "earned": points if selected else 0,
                "missing": 0 if selected else points,
                "selected": selected,
                "description": item["description"],
                "evidence": evidence,
            }
        )
    return rows


def weighted_metric_summary(row: pd.Series) -> dict[str, Any]:
    rows = weighted_metric_rows(row)
    earned = sum(int(r["earned"]) for r in rows)
    possible = sum(int(r["points"]) for r in rows)
    return {
        "earned": earned,
        "possible": possible,
        "missing": max(0, possible - earned),
        "rows": rows,
    }


def metric_selection_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Count how often each scorecard metric is selected across many rows."""
    records: list[dict[str, Any]] = []
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "group",
                "metric",
                "times_selected",
                "times_missing",
                "opportunities",
                "selection_rate",
                "points_earned",
                "points_possible",
            ]
        )

    for _, row in df.iterrows():
        for metric_row in weighted_metric_rows(row):
            records.append(
                {
                    "group": metric_row["group"],
                    "metric": metric_row["metric"],
                    "selected": bool(metric_row["selected"]),
                    "points": int(metric_row["points"]),
                    "earned": int(metric_row["earned"]),
                }
            )

    if not records:
        return pd.DataFrame()

    raw = pd.DataFrame(records)
    grouped = (
        raw.groupby(["group", "metric", "points"], as_index=False)
        .agg(
            times_selected=("selected", "sum"),
            opportunities=("selected", "count"),
            points_earned=("earned", "sum"),
        )
    )
    grouped["times_selected"] = grouped["times_selected"].astype(int)
    grouped["times_missing"] = grouped["opportunities"] - grouped["times_selected"]
    grouped["selection_rate"] = grouped["times_selected"] / grouped["opportunities"]
    grouped["points_possible"] = grouped["points"] * grouped["opportunities"]

    order = {(item["group"], item["metric"]): idx for idx, item in enumerate(SCORING_WEIGHTS)}
    grouped["_order"] = grouped.apply(lambda r: order.get((r["group"], r["metric"]), 999), axis=1)
    return grouped.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)
