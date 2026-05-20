"""
Growth signal processing engine — implements growth_signal_engine.spec.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import pandas as pd

ROLLING_WEEKS = 4


class GrowthTier(str, Enum):
    TIER_STRATEGIST = "TIER_STRATEGIST"
    TIER_OPTIMIZER = "TIER_OPTIMIZER"
    TIER_EXECUTOR = "TIER_EXECUTOR"


TIER_LABELS = {
    GrowthTier.TIER_STRATEGIST: ("Strategist", "🧠"),
    GrowthTier.TIER_OPTIMIZER: ("Optimizer", "⚙️"),
    GrowthTier.TIER_EXECUTOR: ("Executor", "✅"),
}

SIGNAL_LABELS = {
    "signal_mastery_achieved": "Mastery achieved",
    "signal_modesty_gap": "Modesty gap",
    "signal_extra_mile_text": "Extra mile (text)",
    "signal_artifact_provided": "Artifact provided",
    "signal_escalation_quality": "Quality escalation",
}

ALERT_LABELS = {
    "alert_ready_for_stretch": ("Ready for stretch", "Assign Level-Up task"),
    "alert_ceo_mindset_candidate": ("CEO mindset candidate", "Strategic seminar / client-facing"),
    "alert_silent_struggle": ("Silent struggle", "Immediate 1-on-1"),
}


@dataclass
class WeeklySignals:
    signal_mastery_achieved: bool = False
    signal_modesty_gap: bool = False
    signal_extra_mile_text: bool = False
    signal_artifact_provided: bool = False
    signal_escalation_quality: bool = False
    growth_tier: GrowthTier = GrowthTier.TIER_EXECUTOR

    def active_signals(self) -> list[str]:
        out = []
        for name in SIGNAL_LABELS:
            if getattr(self, name):
                out.append(name)
        return out


@dataclass
class LongitudinalAlerts:
    alert_ready_for_stretch: bool = False
    alert_ceo_mindset_candidate: bool = False
    alert_silent_struggle: bool = False

    def active_alerts(self) -> list[str]:
        return [k for k in ALERT_LABELS if getattr(self, k)]


@dataclass
class WeeklyReport:
    """Normalized weekly payload for the engine."""

    QA_completed: float | None = None
    Expected_tickets: float | None = None
    First_pass_QA_percentage: float | None = None
    Overall_rating: float | None = None
    Highlight_text: str = ""
    Upload_URL: str | None = None
    Upload_Document: bool = False
    Expectations_met: bool | None = None
    Challenges_text: str = ""


def _num(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _expectations_met(val: Any) -> bool | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return True
    if s in ("no", "n", "false", "0", "partially", "partial"):
        return False
    return None


def _has_artifact(upload_val: Any) -> tuple[str | None, bool]:
    if upload_val is None or (isinstance(upload_val, float) and pd.isna(upload_val)):
        return None, False
    s = str(upload_val).strip()
    if not s:
        return None, False
    # URL or file reference counts as artifact
    is_url = s.startswith("http://") or s.startswith("https://")
    return (s if is_url else None), True


def row_to_report(row: pd.Series) -> WeeklyReport:
    upload_url, upload_doc = _has_artifact(row.get("upload"))
    return WeeklyReport(
        QA_completed=_num(row.get("tickets_completed")),
        Expected_tickets=_num(row.get("tickets_expected")),
        First_pass_QA_percentage=_num(row.get("qa_first_pass_pct")),
        Overall_rating=_num(row.get("overall_rating")),
        Highlight_text=str(row.get("other_highlights", "") or ""),
        Upload_URL=upload_url,
        Upload_Document=upload_doc,
        Expectations_met=_expectations_met(row.get("met_expectations")),
        Challenges_text=str(row.get("challenges", "") or ""),
    )


def evaluate_weekly_signals(report: WeeklyReport) -> WeeklySignals:
    """Isolated weekly boolean triggers + tier classification."""
    qa = report.QA_completed
    expected = report.Expected_tickets
    qa_pct = report.First_pass_QA_percentage
    rating = report.Overall_rating

    mastery = (
        qa is not None
        and expected is not None
        and expected > 0
        and qa >= expected
        and qa_pct is not None
        and qa_pct >= 95
    )

    modesty = mastery and rating is not None and rating <= 4
    extra_mile = len(report.Highlight_text.strip()) > 15
    artifact = report.Upload_URL is not None or report.Upload_Document
    escalation = (
        report.Expectations_met is False
        and len(report.Challenges_text.strip()) > 50
    )

    signals = WeeklySignals(
        signal_mastery_achieved=mastery,
        signal_modesty_gap=modesty,
        signal_extra_mile_text=extra_mile,
        signal_artifact_provided=artifact,
        signal_escalation_quality=escalation,
    )
    signals.growth_tier = classify_tier(signals)
    return signals


def classify_tier(signals: WeeklySignals) -> GrowthTier:
    if signals.signal_mastery_achieved and (
        signals.signal_extra_mile_text or signals.signal_artifact_provided
    ):
        return GrowthTier.TIER_STRATEGIST
    if signals.signal_mastery_achieved or signals.signal_escalation_quality:
        return GrowthTier.TIER_OPTIMIZER
    return GrowthTier.TIER_EXECUTOR


def evaluate_longitudinal(history: pd.DataFrame) -> LongitudinalAlerts:
    """
    Trailing 4-week window; history must be sorted oldest → newest.
    Expects boolean signal columns on each row.
    """
    alerts = LongitudinalAlerts()
    if history.empty:
        return alerts

    window = history.tail(ROLLING_WEEKS)

    mastery_count = int(window["signal_mastery_achieved"].sum())
    alerts.alert_ready_for_stretch = mastery_count >= 3

    growth_count = int(
        (window["signal_extra_mile_text"] | window["signal_artifact_provided"]).sum()
    )
    alerts.alert_ceo_mindset_candidate = (
        alerts.alert_ready_for_stretch and growth_count >= 3
    )

    if len(history) >= 2:
        last_two = history.tail(2)
        below = last_two.apply(
            lambda r: (
                pd.notna(r.get("tickets_completed"))
                and pd.notna(r.get("tickets_expected"))
                and float(r["tickets_expected"]) > 0
                and float(r["tickets_completed"]) < float(r["tickets_expected"])
            ),
            axis=1,
        )
        short_challenges = last_two["challenges"].fillna("").astype(str).str.strip().str.len() < 15
        alerts.alert_silent_struggle = bool(below.all() and short_challenges.all())

    return alerts


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich all rows with weekly signals, tier, then longitudinal alerts per email."""
    if df.empty:
        return df

    out = df.copy()
    sort_cols = [c for c in ("email", "timestamp") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols)

    weekly_rows: list[dict[str, Any]] = []
    for _, row in out.iterrows():
        sig = evaluate_weekly_signals(row_to_report(row))
        weekly_rows.append(
            {
                **{k: v for k, v in asdict(sig).items() if k != "growth_tier"},
                "growth_tier": sig.growth_tier.value,
            }
        )
    signals_df = pd.DataFrame(weekly_rows, index=out.index)
    out = pd.concat([out, signals_df], axis=1)

    alert_records = []
    for email, group in out.groupby("email", sort=False):
        hist = group.sort_values("timestamp" if "timestamp" in group.columns else "week")
        alerts = evaluate_longitudinal(hist)
        alert_records.append({"email": email, **asdict(alerts)})

    alerts_df = pd.DataFrame(alert_records).set_index("email")
    out = out.join(alerts_df, on="email")
    return out


def signals_to_json(row: pd.Series) -> dict[str, Any]:
    """Export one week's engine output as JSON-friendly dict."""
    sig = {k: bool(row[k]) for k in SIGNAL_LABELS if k in row.index}
    return {
        "weekly_signals": sig,
        "growth_tier": row.get("growth_tier"),
        "longitudinal_alerts": {
            k: bool(row[k]) for k in ALERT_LABELS if k in row.index
        },
    }
