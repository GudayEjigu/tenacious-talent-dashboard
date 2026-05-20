# Growth Signal Engine — Specification

## 1. System Objective

Build a processing engine that ingests self-reported weekly talent data, evaluates it against strict Boolean logic thresholds, and outputs **Growth Signals** and **Trajectory Alerts** for the management dashboard. Do not build a data-entry UI; build the logic engine that processes the JSON payloads.

## 2. Weekly Signal Triggers (Isolated Logic)

Evaluate these boolean flags every time a new weekly report is ingested.

| Signal | Trigger | Meaning |
|--------|---------|---------|
| `signal_mastery_achieved` | `(QA_completed >= Expected_tickets) AND (First_pass_QA_percentage >= 95)` | Outperforming baseline SLA; workload may be too easy. |
| `signal_modesty_gap` | `signal_mastery_achieved == TRUE AND Overall_rating <= 4` | High performer with a high internal bar. |
| `signal_extra_mile_text` | `Length(Highlight_text) > 15` | Proactively sharing insights without being forced. |
| `signal_artifact_provided` | `Upload_URL != NULL OR Upload_Document == TRUE` | Tangible proof of challenge/win. |
| `signal_escalation_quality` | `Expectations_met == FALSE AND Length(Challenges_text) > 50` | Missed target but detailed, proactive explanation. |

## 3. Longitudinal Alerts (Aggregated Logic)

Evaluate using a **trailing 4-week rolling window** per talent.

| Alert | Trigger | Action output |
|-------|---------|---------------|
| `alert_ready_for_stretch` | `signal_mastery_achieved` TRUE in **≥ 3 of last 4 weeks** | Flag for Level-Up task. |
| `alert_ceo_mindset_candidate` | `(signal_extra_mile_text OR signal_artifact_provided)` TRUE in **≥ 3 of last 4 weeks** AND `alert_ready_for_stretch` | Flag for strategic seminar / client-facing discussion. |
| `alert_silent_struggle` | `QA_completed < Expected_tickets` for **2 consecutive weeks** AND `Length(Challenges_text) < 15` | Flag for immediate 1-on-1. |

## 4. Automated Growth Tier Classification

Assign one enum per week after signals are calculated:

| Tier | Requires |
|------|----------|
| `TIER_STRATEGIST` | `signal_mastery_achieved` AND (`signal_extra_mile_text` OR `signal_artifact_provided`) |
| `TIER_OPTIMIZER` | `signal_mastery_achieved` OR `signal_escalation_quality` |
| `TIER_EXECUTOR` | Default when baseline met but no growth signals |

Priority: evaluate STRATEGIST first, then OPTIMIZER, else EXECUTOR.

## 5. Field mapping (sheet → engine)

| Engine field | Sheet column (internal) |
|--------------|-------------------------|
| `QA_completed` | `tickets_completed` |
| `Expected_tickets` | `tickets_expected` |
| `First_pass_QA_percentage` | `qa_first_pass_pct` |
| `Overall_rating` | `overall_rating` |
| `Highlight_text` | `other_highlights` |
| `Upload_URL` | `upload` |
| `Expectations_met` | `met_expectations` (`Yes` = TRUE) |
| `Challenges_text` | `challenges` |
