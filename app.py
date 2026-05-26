"""Weekly Telegram check-ins — HR Talent Status and Progress Viewer."""

import datetime
import pandas as pd
import streamlit as st

from data_loader import get_secret, load_sheet
from weekly_checks import (
    Check,
    display_name,
    format_week_label,
    person_summary_checks,
    person_weeks,
    week_checks,
    TALENT_ROSTER,
)
import notables
import scoring
import growth_signal_engine
import os

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHOdZugsQlciIwFckKYXqHGn8NBlXdLHJwFf3KxuabSdtXX6rlunWMx7yegMiQK6cSckTTiX6ISsH4/pub?gid=0&single=true&output=csv"

st.set_page_config(
    page_title="Talent management weekly overview",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Styling & CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stMarkdownContainer"], button, input, select, textarea, table, td, th, p, h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Prevent icon fonts from being overridden by Montserrat */
    [data-testid="stIconMaterial"], .material-icons, [class*="Icon"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    }

    /* Original check-in badges converted to transparent list bullets */
    .check-ok   { padding: 4px 0 !important; margin: 2px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.95rem !important; }
    .check-warn { padding: 4px 0 !important; margin: 2px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.95rem !important; }
    .check-watch{ padding: 4px 0 !important; margin: 2px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.95rem !important; }
    .week-head  { font-size: 1.2rem; font-weight: 700; margin: 1rem 0 0.5rem 0; }
    .answer-box { background: #f8f9fa; padding: 0.75rem 1rem; border-radius: 8px;
                  margin: 0.35rem 0 0.75rem 0; white-space: pre-wrap; font-size: 0.95rem; color: #334155; }
                  
    /* HR Row container styles */
    .hr-row {
        display: flex;
        align-items: center;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        background: #ffffff;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        border: 1px solid #eef2f6;
        transition: all 0.2s ease-in-out;
    }
    .hr-row:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        border-color: #cbd5e1;
    }
    
    .name-section {
        width: 250px;
        flex-shrink: 0;
    }
    .name-text {
        font-weight: 700;
        font-size: 1.05rem;
        color: #1e293b;
    }
    .email-text {
        font-size: 0.8rem;
        color: #64748b;
    }
    
    .badge-section {
        width: 200px;
        flex-shrink: 0;
        padding: 0 10px;
        text-align: left;
    }
    
    /* HR Pill Badges */
    .hr-badge {
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        text-align: center;
        display: inline-block;
        white-space: nowrap;
    }
    .status-concern { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
    .status-qa-concern { background: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }
    .status-mixed { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .status-solid { background: #e6fcf5; color: #0c8599; border: 1px solid #99e9f2; }
    .status-excelling { background: #ebfbee; color: #2b8a3e; border: 1px solid #b2f2bb; }
    .status-incomplete { background: #f1f3f5; color: #495057; border: 1px solid #dee2e6; }
    
    .reason-section {
        flex-grow: 1;
        padding-left: 15px;
        font-size: 0.95rem;
        color: #334155;
        line-height: 1.4;
    }
    
    /* Quick Details Card */
    .detail-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-top: 1rem;
    }
    .detail-section-title {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.05em;
        margin-top: 0.75rem;
        margin-bottom: 0.35rem;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 3px;
    }
    
    /* Custom Premium HTML Table */
    .custom-table-container {
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        margin: 1.5rem 0;
        background-color: white;
    }
    table.custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: inherit;
        color: #334155;
        font-size: 0.9rem;
        text-align: left;
    }
    table.custom-table th {
        background-color: #f8fafc;
        color: #475569;
        font-weight: 600;
        padding: 12px 16px;
        border-bottom: 2px solid #e2e8f0;
        white-space: nowrap;
    }
    table.custom-table td {
        padding: 0 !important; /* Let block cell-links handle the padding */
        border-bottom: 1px solid #f1f5f9;
        vertical-align: middle;
        white-space: normal;
        word-break: break-word;
    }
    table.custom-table tbody tr {
        transition: all 0.2s ease-in-out;
    }
    table.custom-table tbody tr:hover {
        background-color: #eff6ff !important;
    }
    table.custom-table tbody tr:hover td:first-child {
        box-shadow: inset 3px 0 0 0 #3b82f6; /* Left border accent indicator */
    }
    table.custom-table tbody tr:active {
        background-color: #dbeafe !important;
    }
    .cell-link {
        display: block;
        width: 100%;
        height: 100%;
        padding: 12px 16px;
        color: inherit !important;
        text-decoration: none !important;
        box-sizing: border-box;
        cursor: pointer;
    }
    .cell-link:hover {
        text-decoration: none !important;
    }
    .nowrap-column {
        white-space: nowrap !important;
    }
    .talent-td {
        padding: 0 !important;
    }

    /* Premium Sidebar Styling (Light Theme) */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important; /* Premium Pure White */
        border-right: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] hr {
        border-top: 1px solid #e2e8f0 !important;
        margin: 1.25rem 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #334155 !important; /* Slate / Charcoal */
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #1e3b70 !important; /* Deep Navy from logo */
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] label {
        color: #1e3b70 !important; /* Deep Navy */
        font-weight: 700 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.4rem !important;
    }
    /* Buttons inside st.button wrapper in light sidebar (unclicked/outline style) */
    [data-testid="stSidebar"] [data-testid="stButton"] button {
        background-color: #ffffff !important; /* Pure white background */
        border: 2px solid #585ba6 !important; /* Brand purple-blue border */
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button p, 
    [data-testid="stSidebar"] [data-testid="stButton"] button span, 
    [data-testid="stSidebar"] [data-testid="stButton"] button div {
        color: #585ba6 !important; /* Brand purple-blue text */
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background-color: #585ba6 !important; /* Brand purple-blue filled on hover */
        border-color: #585ba6 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 10px rgba(88, 91, 166, 0.15) !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover p, 
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover span, 
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover div {
        color: #ffffff !important; /* White text on hover */
    }

    /* Selected state styling for st.segmented_control and st.pills in sidebar */
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] button[aria-selected="true"],
    [data-testid="stSidebar"] button[data-selected="true"],
    [data-testid="stSidebar"] div[data-testid="stPills"] button[aria-selected="true"],
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[aria-selected="true"],
    [data-testid="stSidebar"] div[class*="stPills"] button[aria-selected="true"],
    [data-testid="stSidebar"] div[class*="stSegmentedControl"] button[aria-selected="true"] {
        background-color: #585ba6 !important; /* Purple-blue from logo */
        color: #ffffff !important;
        border: 1px solid #585ba6 !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] p,
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] span,
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] div,
    [data-testid="stSidebar"] button[aria-selected="true"] p, 
    [data-testid="stSidebar"] button[aria-selected="true"] span, 
    [data-testid="stSidebar"] button[aria-selected="true"] div,
    [data-testid="stSidebar"] button[data-selected="true"] p,
    [data-testid="stSidebar"] button[data-selected="true"] span,
    [data-testid="stSidebar"] button[data-selected="true"] div {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Unselected state styling for st.segmented_control and st.pills in sidebar */
    [data-testid="stSidebar"] button[aria-selected="false"],
    [data-testid="stSidebar"] button[data-selected="false"],
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] div[class*="stPills"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] div[class*="stSegmentedControl"] button[data-testid="stBaseButton-secondary"] {
        background-color: #f8fafc !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] button[aria-selected="false"] p, 
    [data-testid="stSidebar"] button[aria-selected="false"] span, 
    [data-testid="stSidebar"] button[aria-selected="false"] div,
    [data-testid="stSidebar"] button[data-selected="false"] p,
    [data-testid="stSidebar"] button[data-selected="false"] span,
    [data-testid="stSidebar"] button[data-selected="false"] div,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"] p,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"] span,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"] div,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"] p,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"] span,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"] div {
        color: #475569 !important;
    }
    [data-testid="stSidebar"] button[aria-selected="false"]:hover,
    [data-testid="stSidebar"] button[data-selected="false"]:hover,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"]:hover,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #f1f5f9 !important;
        border-color: #cbd5e1 !important;
    }
    [data-testid="stSidebar"] button[aria-selected="false"]:hover p, 
    [data-testid="stSidebar"] button[aria-selected="false"]:hover span, 
    [data-testid="stSidebar"] button[aria-selected="false"]:hover div,
    [data-testid="stSidebar"] button[data-selected="false"]:hover p,
    [data-testid="stSidebar"] button[data-selected="false"]:hover span,
    [data-testid="stSidebar"] button[data-selected="false"]:hover div,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"]:hover p,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"]:hover span,
    [data-testid="stSidebar"] div[data-testid="stPills"] button[data-testid="stBaseButton-secondary"]:hover div,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"]:hover p,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"]:hover span,
    [data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button[data-testid="stBaseButton-secondary"]:hover div {
        color: #1e3b70 !important; /* Deep Navy */
    }

    [data-testid="stSidebar"] p {
        color: #64748b !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

CSS = {"ok": "check-ok", "warn": "check-warn", "watch": "check-watch"}
ICON = {"ok": "", "warn": "", "watch": ""}

# --- Work Tag Analysis & Inline Rendering ---
def extract_achievements_tags(text: str) -> list[str]:
    if not text or not isinstance(text, str):
        return []
    
    text_lower = text.lower()
    tags = []
    
    categories = [
        (["qa", "test", "unittest", "pytest", "cypress", "selenium", "integration test", "e2e"], "QA & Testing"),
        (["bug", "fix", "issue", "debug", "resolv", "error", "hotfix", "patch"], "Bug Fixing"),
        (["ui", "ux", "frontend", "css", "react", "html", "view", "component", "screen", "button", "layout", "page", "styling", "tailwind", "responsive", "design"], "Frontend & UI"),
        (["backend", "api", "database", "sql", "django", "fastapi", "server", "endpoint", "models", "query", "graphql", "postgres", "redis", "schema"], "Backend & API"),
        (["devops", "docker", "ci/cd", "pipeline", "aws", "deploy", "gcp", "kubernetes", "git", "github", "actions", "scripts"], "DevOps & CI-CD"),
        (["doc", "wiki", "readme", "guide", "write-up", "swagger", "postman", "documentation"], "Documentation"),
        (["refactor", "cleanup", "optimize", "performance", "clean", "speed", "refactoring", "caching", "query optimization"], "Optimization & Refactoring"),
        (["meeting", "sync", "scrum", "agile", "sprint", "client", "interview", "demo", "standup", "presentation"], "Meetings & Team Sync"),
        (["research", "learn", "study", "spike", "investigat", "explore", "documentation reading"], "Research & Learning"),
        (["migration", "db migration", "liquibase", "flyway"], "Database Migration"),
    ]
    
    for keywords, label in categories:
        if any(kw in text_lower for kw in keywords):
            tags.append(label)
            
    if not tags and text.strip():
        tags.append("General Tasks")
        
    return tags

def extract_challenges_tags(text: str) -> list[str]:
    if not text or not isinstance(text, str):
        return []
    
    text_lower = text.lower()
    tags = []
    
    categories = [
        (["block", "wait", "api block", "blocked", "dependency", "wait for backend", "waiting on"], "Blocked by Dependency"),
        (["bug", "fix", "stuck", "hard bug", "debugging", "regression"], "Difficult Bug/Debug"),
        (["setup", "config", "install", "environment", "toolchain", "docker issue", "npm issue", "venv"], "Environment/Setup Issues"),
        (["merge", "conflict", "git conflict", "branching", "rebase"], "Merge Conflicts & Git"),
        (["scope", "change", "creep", "requirement", "unclear"], "Unclear Requirements"),
        (["complex", "logic", "algorithm", "difficult", "architecture", "understanding code"], "Complex Logic"),
        (["estimate", "time constraint", "estimation", "deadline", "delay"], "Time/Deadline Constraints"),
        (["time management", "prioriti", "distraction", "focus"], "Time Management & Focus"),
        (["communicat", "team", "review", "delay in review", "slack response"], "Communication Delay"),
        (["internet", "power", "electricity", "slow connection", "vpn", "outage"], "Connectivity/Power Issues"),
        (["learn", "new tech", "understanding", "tutorial", "learning curve", "framework syntax"], "Technical Learning Curve"),
        (["tech debt", "refactoring", "legacy code", "old code"], "Legacy Code/Tech Debt"),
    ]
    
    for keywords, label in categories:
        if any(kw in text_lower for kw in keywords):
            tags.append(label)
            
    if not tags and text.strip():
        tags.append("General Challenges")
        
    return tags

def render_tags_inline(tags: list[str]) -> str:
    if not tags:
        return ""
    import html
    escaped_tags = [html.escape(t) for t in tags]
    joined_text = ", ".join(escaped_tags)
    return f'<span style="color: #475569; font-weight: 600; font-size: 0.85rem;">{joined_text}</span>'




def _render_check(c: Check) -> None:
    if c.status == "ok":
        bullet_color = "#4ade80"  # Very light premium emerald green
    elif c.status == "warn":
        bullet_color = "#fca5a5"  # Very light premium coral red
    else:  # watch
        bullet_color = "#fbbf24"  # Very light premium amber yellow
        
    st.markdown(
        f'<div class="{CSS[c.status]}" style="display: flex; align-items: center; margin: 4px 0;">'
        f'<span style="color: {bullet_color}; font-size: 1.15rem; margin-right: 8px; line-height: 1; vertical-align: middle;">●</span>'
        f'<span style="line-height: 1.4;"><b>{c.label}</b>{": " + c.detail if c.detail else ""}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300, show_spinner="Loading and enriching sheet data…")
def _load_enriched(csv_url: str | None = None):
    raw_df, parse_info = load_sheet(csv_url)
    
    # Clean future entries based on current local timestamp: May 20, 2026
    if "timestamp" in raw_df.columns:
        cutoff = pd.Timestamp("2026-05-20 23:59:59")
        raw_df["temp_ts"] = pd.to_datetime(raw_df["timestamp"]).dt.tz_localize(None)
        raw_df = raw_df[raw_df["temp_ts"] <= cutoff].drop(columns=["temp_ts"])
    
    # Map duplicate email aliases and keep only active talents from TALENT_ROSTER
    if "email" in raw_df.columns:
        raw_df["email"] = raw_df["email"].str.strip().str.lower()
        
        EMAIL_ALIASES = {
            "smlnegash@gmail.com": "samuel@gettenacious.com",
            "belay@10academy.org": "belay@gettenacious.com",
            "alazar.getachew@coraloyalty.com": "alazar@gettenacious.com",
            "lillianalehegn123@gmail.com": "lillian@gettenacious.com",
            "mamamohammed31@gmail.com": "mama@gettenacious.com",
            "nahom.fix@gmail.com": "nahom@gettenacious.com",
            "meronabdo954@gmail.com": "meron@gettenacious.com",
        }
        raw_df["email"] = raw_df["email"].replace(EMAIL_ALIASES)
        
        # Filter strictly to active talents from the roster
        raw_df = raw_df[raw_df["email"].isin(TALENT_ROSTER.keys())]

    
    # Process weekly signals & longitudinal alerts
    df_engine = growth_signal_engine.process_dataframe(raw_df)
    df_engine["spec_growth_tier"] = df_engine["growth_tier"]
    
    # Add numerical metrics for reason compiling
    df_scored = scoring.enrich_dataframe(df_engine.drop(columns=["growth_tier"]))
    df_scored["growth_tier"] = df_scored["spec_growth_tier"]
    
    return df_scored, parse_info


def generate_hr_explanation(row) -> tuple[str, str, str, str]:
    """
    Returns: (status_label, emoji, css_class, short_explanation)
    Constructs a plain English dynamic sentence explaining weekly performance status.
    """
    completed = row.get("tickets_completed")
    expected = row.get("tickets_expected")
    qa = row.get("qa_first_pass_pct")
    rating = row.get("overall_rating")
    
    # Check flags
    mastery = bool(row.get("signal_mastery_achieved", False))
    modesty = bool(row.get("signal_modesty_gap", False))
    extra_mile = bool(row.get("signal_extra_mile_text", False))
    artifact = bool(row.get("signal_artifact_provided", False))
    escalation = bool(row.get("signal_escalation_quality", False))
    
    # Check alerts
    silent_struggle = bool(row.get("alert_silent_struggle", False))
    ready_stretch = bool(row.get("alert_ready_for_stretch", False))
    ceo_mindset = bool(row.get("alert_ceo_mindset_candidate", False))
    
    reasons = []
    
    # Determine baseline status
    if pd.notna(completed) and pd.notna(expected) and expected > 0:
        ratio = completed / expected
        if ratio < 0.7:
            status = "Struggling / Concern"
            emoji = ""
            css_class = "status-concern"
            reasons.append(f"completed only {int(completed)} of {int(expected)} expected tickets ({ratio:.0%})")
        elif ratio >= 1.0 and qa is not None and qa >= 95:
            status = "Excelling / High Growth"
            emoji = ""
            css_class = "status-excelling"
            reasons.append(f"exceeded ticket targets ({int(completed)}/{int(expected)}) with high QA first-pass ({qa:.0f}%)")
        elif ratio >= 0.8:
            status = "Solid / Baseline Met"
            emoji = ""
            css_class = "status-solid"
            reasons.append(f"completed {int(completed)} of {int(expected)} expected tickets")
        else:
            status = "Mixed Performance"
            emoji = "🟠"
            css_class = "status-mixed"
            reasons.append(f"completed {int(completed)} of {int(expected)} expected tickets (below 80% SLA)")
    else:
        status = "Incomplete Metrics"
        emoji = ""
        css_class = "status-incomplete"
        reasons.append("didn't provide standard ticket metrics")

    # Add QA considerations
    if qa is not None and len(reasons) > 0 and "QA" not in reasons[0]:
        if qa >= 90:
            reasons.append(f"excellent QA first-pass rate of {qa:.0f}%")
        elif qa < 80:
            reasons.append(f"low first-pass QA rate of {qa:.0f}%")
            if css_class != "status-concern":  # Upgrade warning to QA Concern
                css_class = "status-qa-concern"
                status = "QA Quality Concern"
                emoji = "🟠"

    # Add proactivity highlights
    details = []
    if extra_mile:
        details.append("shared rich optional insights")
    if artifact:
        details.append("provided document/link evidence of work")
    if escalation:
        details.append("offered a detailed proactive explanation of missed targets")
    if modesty:
        details.append("outperformed SLA but rated self modestly")
        
    if details:
        reasons.append("proactively " + " and ".join(details))
        
    # Long-term alerts
    alerts_note = []
    if silent_struggle:
        alerts_note.append("Silent Struggle alert: Underperformed tickets for consecutive weeks with very short explanations.")
    if ceo_mindset:
        alerts_note.append("🧠 Exceptional leadership potential (CEO-mindset candidate).")
    elif ready_stretch:
        alerts_note.append("Ready for stretch/Level-Up tasks.")

    # Combine into short natural sentence
    explanation = ""
    if reasons:
        explanation = "They " + reasons[0]
        if len(reasons) > 1:
            explanation += " with " + ", and ".join(reasons[1:])
        explanation += "."
        
    if alerts_note:
        explanation += " " + " ".join(alerts_note)
        
    return status, emoji, css_class, explanation


def get_sort_weight(row: pd.Series) -> int:
    # 1. Put missing submissions at the absolute bottom
    if not row.get("has_submission", False):
        return 100
        
    # 2. Sort warnings and concerns at the very top
    status = row.get("hr_status")
    weights = {
        "Struggling / Concern": 1,
        "QA Quality Concern": 2,
        "Mixed Performance": 3,
        "Incomplete Metrics": 4,
        "Solid / Baseline Met": 5,
        "Excelling / High Growth": 6
    }
    return weights.get(status, 10)


# --- Load & Clean Data ---
# Initialize session state variables for uploaded data
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None
if "uploaded_parse_info" not in st.session_state:
    st.session_state.uploaded_parse_info = None

df = None
parse_info = None

# 1. First, check if there is an uploaded or pre-loaded dataframe in session state
if st.session_state.uploaded_df is not None:
    df = st.session_state.uploaded_df
    parse_info = st.session_state.uploaded_parse_info
else:
    # 2. Next, try loading from the configured Secret URL or the DEFAULT_SHEET_URL
    active_url = get_secret("sheet_csv_url", "").strip() or DEFAULT_SHEET_URL
    if active_url:
        try:
            df, parse_info = _load_enriched(active_url)
        except Exception as e:
            # Let it fail gracefully and fall back to the welcome screen
            pass

# 3. If no data has been loaded, display the beautiful branded setup/upload screen!
if df is None:
    st.title("📊 Tenacious Growth Dashboard")
    st.markdown("### Welcome! Let's connect your weekly check-in data.")
    st.info(
        "To get started, you can either **upload a CSV export** of your Google Sheet directly, "
        "or **paste a shared Google Sheets link**."
    )
    
    tab_upload, tab_link = st.tabs(["📁 Upload CSV File (Private & Local)", "🔗 Link Google Sheet"])
    
    with tab_upload:
        st.markdown("#### 1. Download your Google Sheet as a CSV file:")
        st.markdown(
            "In your Google Sheet, click **File** ➔ **Download** ➔ **Comma-separated values (.csv)**"
        )
        uploaded_file = st.file_uploader("Upload check-ins.csv", type=["csv"], key="main_csv_uploader")
        if uploaded_file is not None:
            try:
                import io
                text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
                from data_loader import _parse_csv_text, _coerce_types, _normalize_columns, validate_sheet_dataframe
                raw_df, p_info = _parse_csv_text(text)
                raw_df = _coerce_types(_normalize_columns(raw_df))
                validate_sheet_dataframe(raw_df)
                
                # Enrich using existing logic
                df_engine = growth_signal_engine.process_dataframe(raw_df)
                df_engine["spec_growth_tier"] = df_engine["growth_tier"]
                df_scored = scoring.enrich_dataframe(df_engine.drop(columns=["growth_tier"]))
                df_scored["growth_tier"] = df_scored["spec_growth_tier"]
                
                st.session_state.uploaded_df = df_scored
                st.session_state.uploaded_parse_info = p_info
                st.success("✅ CSV uploaded and parsed successfully!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error parsing uploaded CSV: {ex}")
                
    with tab_link:
        st.markdown("#### Paste your Google Sheet sharing link:")
        st.info(
            "💡 **Important:** Make sure the sheet's general access is set to **'Anyone with the link can view'** "
            "so the dashboard can fetch the data automatically."
        )
        override = st.text_input("Google Sheets Link (shared or published CSV URL)", value=get_secret("sheet_csv_url", ""))
        if override:
            try:
                st.cache_data.clear()
                df_scored, p_info = _load_enriched(override)
                st.session_state.uploaded_df = df_scored
                st.session_state.uploaded_parse_info = p_info
                st.success("✅ Linked to Google Sheet successfully!")
                st.rerun()
            except Exception as e2:
                st.error(f"Could not load from Google Sheet link: {e2}")
                
    st.stop()

if parse_info and (parse_info.repaired_rows or parse_info.skipped_rows):
    st.warning(
        f"Parsed with repairs: {parse_info.repaired_rows} fixed, {parse_info.skipped_rows} skipped."
    )

if "email" not in df.columns:
    st.error("No email column in sheet.")
    st.stop()

df["talent"] = df["email"].map(display_name)
# All known talents from the roster
_all_people = sorted(list({e for e in TALENT_ROSTER.keys() if e.endswith("@gettenacious.com")}))
# Only keep people who have submitted at least once
_submitted_emails = set(df["email"].dropna().unique())
people = [e for e in _all_people if e in _submitted_emails]
name_by_email = {e: display_name(e) for e in people}

# Filter valid unique weeks globally so they are available in both views
unique_weeks = sorted(df["week"].dropna().unique().tolist())
unique_weeks = [w for w in unique_weeks if w and str(w) != "NaT"]

# --- Session State Initialization ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Talent Weekly Status"
if "selected_talent" not in st.session_state:
    st.session_state.selected_talent = people[0] if people else None

# --- Handle Query Parameters for Navigation ---
if "selected_talent" in st.query_params:
    tgt_talent = st.query_params["selected_talent"]
    if tgt_talent in people:
        st.session_state.selected_talent = tgt_talent
        st.session_state.view_mode = "Talent Profiles"
    st.query_params.clear()

# --- Sidebar Navigation ---
with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)
    
    if st.session_state.selected_talent not in people and people:
        st.session_state.selected_talent = people[0]
        
    nav_options = ["Talent Weekly Status", "Talent Profiles"]
    
    view_mode = st.segmented_control(
        "Navigation",
        nav_options,
        selection_mode="single",
        default=st.session_state.view_mode,
        key="view_mode_control"
    )
    if view_mode:
        st.session_state.view_mode = view_mode
    else:
        view_mode = st.session_state.view_mode
    
    st.markdown("---")
    
    if st.button("↻ Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    if st.session_state.uploaded_df is not None:
        if st.button("📁 Reset / Load New Sheet", use_container_width=True):
            st.session_state.uploaded_df = None
            st.session_state.uploaded_parse_info = None
            st.cache_data.clear()
            st.rerun()
        
    st.caption(f"{len(people)} team members · {len(df)} check-ins")

# --- VIEW: TALENT WEEKLY STATUS (LANDING PAGE) ---
if view_mode == "Talent Weekly Status":
    if not unique_weeks:
        st.info("No weekly data available.")
        st.stop()
        
    # Maintain selected week in session state
    if "week_idx" not in st.session_state:
        st.session_state.week_idx = len(unique_weeks) - 1
    elif st.session_state.week_idx >= len(unique_weeks):
        st.session_state.week_idx = len(unique_weeks) - 1
        
    active_week_str = unique_weeks[st.session_state.week_idx]
    
    # Format the active week date (e.g. "Week of 2 March 2026")
    start_date_str = active_week_str.split("/")[0]
    try:
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        day = str(start_dt.day)
        month = start_dt.strftime("%b")
        year = start_dt.strftime("%Y")
        formatted_week_title = f"Week of {day} {month} {year}"
    except Exception:
        formatted_week_title = f"Week {active_week_str}"
        
    # Title & Pagination Header
    st.title("Talent management weekly overview")
    st.caption("Weekly telegram bot data")
    
    col_prev, col_title, col_next = st.columns([1.5, 4, 1.5])
    with col_prev:
        prev_enabled = st.session_state.week_idx > 0
        if st.button("◀ Previous Week", disabled=not prev_enabled, use_container_width=True):
            st.session_state.week_idx -= 1
            st.rerun()
    with col_title:
        st.markdown(f"<h3 style='text-align: center; margin:0; padding-top:4px; color:#1e3a8a;'>{formatted_week_title}</h3>", unsafe_allow_html=True)
    with col_next:
        next_enabled = st.session_state.week_idx < len(unique_weeks) - 1
        if st.button("Next Week ▶", disabled=not next_enabled, use_container_width=True):
            st.session_state.week_idx += 1
            st.rerun()
            
    # Load and filter week's data
    week_df = df[df["week"] == active_week_str].copy()
    
    # Build complete record list for ALL possible unique talents
    week_records = []
    for email in people:
        talent_rows = week_df[week_df["email"] == email]
        talent_name = name_by_email.get(email, display_name(email))

        # Find this talent's first-ever submission week
        talent_all = df[df["email"] == email]
        if talent_all.empty:
            # Never submitted — skip entirely
            continue
        first_week = talent_all["week"].dropna().min()
        # Skip this talent for weeks before they ever submitted
        if first_week and active_week_str < first_week:
            continue
        
        if not talent_rows.empty:
            # Talent submitted check-in
            row = talent_rows.iloc[0].copy()
            status_lbl, status_emoji, status_css, explanation_text = generate_hr_explanation(row)
            
            ts = row.get("timestamp")
            ts_val = ts.strftime("%d/%m/%Y %H:%M:%S") if pd.notna(ts) else ""
            
            completed = row.get("tickets_completed")
            completed_val = str(int(completed)) if pd.notna(completed) else ""
            
            expected = row.get("tickets_expected")
            expected_val = str(int(expected)) if pd.notna(expected) else ""
            
            qa = row.get("qa_first_pass_pct")
            qa_val = f"{int(qa)}%" if pd.notna(qa) else ""
            
            rating = row.get("overall_rating")
            rating_val = str(int(rating)) if pd.notna(rating) else ""
            
            week_records.append({
                "Talent": talent_name,
                "Timestamp": ts_val,
                "Email address": email,
                "What were your key achievements of the week?": row.get("key_achievements", ""),
                "Number of tickets actually completed QA or Done?": completed_val,
                "Expected number of tickets to get completed": expected_val,
                "% of tickets that passed QA on first attempt": qa_val,
                "What were your challenges of the week?": row.get("challenges", ""),
                "Have you met all the expectations of your employer for this week?": row.get("met_expectations", ""),
                "Overall rating of your performance this week?": rating_val,
                "Write here any other things you want to highlight (optional)": row.get("other_highlights", ""),
                "Upload any image or document you want us to see (optional)": row.get("upload", ""),
                "email": email,
                "has_submission": True,
                "hr_status": status_lbl,
                "hr_emoji": status_emoji,
                "hr_css": status_css,
                "hr_explanation": explanation_text,
                "key_achievements": row.get("key_achievements", ""),
                "challenges": row.get("challenges", ""),
                "other_highlights": row.get("other_highlights", ""),
                "overall_rating": row.get("overall_rating"),
                "met_expectations": row.get("met_expectations"),
                "tickets_completed": row.get("tickets_completed"),
                "tickets_expected": row.get("tickets_expected"),
                "qa_first_pass_pct": row.get("qa_first_pass_pct"),
            })
        else:
            # Missing submission for this week
            week_records.append({
                "Talent": talent_name,
                "Timestamp": "",
                "Email address": email,
                "What were your key achievements of the week?": "",
                "Number of tickets actually completed QA or Done?": "",
                "Expected number of tickets to get completed": "",
                "% of tickets that passed QA on first attempt": "",
                "What were your challenges of the week?": "",
                "Have you met all the expectations of your employer for this week?": "",
                "Overall rating of your performance this week?": "",
                "Write here any other things you want to highlight (optional)": "",
                "Upload any image or document you want us to see (optional)": "",
                "email": email,
                "has_submission": False,
                "hr_status": "Missing Submission",
                "hr_emoji": "",
                "hr_css": "status-incomplete",
                "hr_explanation": "Did not submit a check-in for this week.",
                "key_achievements": "",
                "challenges": "",
                "other_highlights": "",
                "overall_rating": None,
                "met_expectations": "",
                "tickets_completed": None,
                "tickets_expected": None,
                "qa_first_pass_pct": None,
            })
            
    week_full_df = pd.DataFrame(week_records)
    # Sort alphabetically by Talent (name)
    week_full_df = week_full_df.sort_values(by="Talent").reset_index(drop=True)
    
    if week_full_df.empty:
        st.warning("No talent list found in database.")
    else:
        st.markdown("---")
        display_headers = [
            "Talent", "Timestamp", "Email address", "Achievements (Tags)",
            "Tickets Completed", "Expected Tickets", "QA First-Pass %", "Challenges (Tags)",
            "Met Expectations", "Rating", "Other Highlights", "Attachment"
        ]
        
        col_to_df_key = {
            "Talent": "Talent",
            "Timestamp": "Timestamp",
            "Email address": "Email address",
            "Achievements (Tags)": "What were your key achievements of the week?",
            "Tickets Completed": "Number of tickets actually completed QA or Done?",
            "Expected Tickets": "Expected number of tickets to get completed",
            "QA First-Pass %": "% of tickets that passed QA on first attempt",
            "Challenges (Tags)": "What were your challenges of the week?",
            "Met Expectations": "Have you met all the expectations of your employer for this week?",
            "Rating": "Overall rating of your performance this week?",
            "Other Highlights": "Write here any other things you want to highlight (optional)",
            "Attachment": "Upload any image or document you want us to see (optional)"
        }
        
        import html
        
        html_lines = []
        html_lines.append('<div class="custom-table-container">')
        html_lines.append('  <table class="custom-table">')
        
        # Table Header
        html_lines.append('    <thead>')
        html_lines.append('      <tr>')
        for header in display_headers:
            html_lines.append(f'        <th>{html.escape(header)}</th>')
        html_lines.append('      </tr>')
        html_lines.append('    </thead>')
        
        # Table Body
        html_lines.append('    <tbody>')
        for idx, row in week_full_df.iterrows():
            email = row.get("email", "")
            html_lines.append('      <tr>')
            for header in display_headers:
                df_key = col_to_df_key[header]
                val = row.get(df_key, "")
                if pd.isna(val):
                    val = ""
                
                if header == "Talent":
                    name = row.get("Talent", "")
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link" style="color: #1e3a8a !important; font-weight: 600;">👤 {html.escape(name)}</a>'
                    html_lines.append(f'        <td class="talent-td nowrap-column">{cell_html}</td>')
                elif header in ("Timestamp", "Email address"):
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link">{html.escape(str(val))}</a>'
                    html_lines.append(f'        <td class="nowrap-column">{cell_html}</td>')
                elif header == "Achievements (Tags)":
                    tags = extract_achievements_tags(str(val))
                    tags_html = render_tags_inline(tags)
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link">{tags_html}</a>'
                    html_lines.append(f'        <td>{cell_html}</td>')
                elif header == "Challenges (Tags)":
                    tags = extract_challenges_tags(str(val))
                    tags_html = render_tags_inline(tags)
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link">{tags_html}</a>'
                    html_lines.append(f'        <td>{cell_html}</td>')
                elif header == "Attachment":
                    val_str = str(val).strip()
                    if val_str and val_str.startswith("http"):
                        link_html = f'<a href="{html.escape(val_str)}" target="_blank" style="color: #3b82f6; font-weight: 600; text-decoration: underline; display: block; padding: 12px 16px;">Open Link</a>'
                        html_lines.append(f'        <td>{link_html}</td>')
                    else:
                        cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link">{html.escape(val_str)}</a>'
                        html_lines.append(f'        <td>{cell_html}</td>')
                else:
                    escaped_val = html.escape(str(val))
                    formatted_val = escaped_val.replace("\n", "<br/>")
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link">{formatted_val}</a>'
                    html_lines.append(f'        <td>{cell_html}</td>')
            html_lines.append('      </tr>')
        html_lines.append('    </tbody>')
        html_lines.append('  </table>')
        html_lines.append('</div>')
        
        html_table = "\n".join(html_lines)
        st.markdown(html_table, unsafe_allow_html=True)

            
        # --- Interactive Drill-Down Section ---
        st.markdown("---")
        
        # Only show talents who actually submitted a check-in in the dropdown
        submitted_talents = week_full_df[week_full_df["has_submission"] == True]["email"].tolist()
        
        if not submitted_talents:
            st.info("No check-ins submitted this week to inspect.")
        else:
            st.markdown("### Select a team member to read their exact answers for this week:")
            selected_email_drill = st.selectbox(
                "Select a team member to read their exact answers for this week:",
                submitted_talents,
                format_func=lambda e: name_by_email.get(e, display_name(e)),
                label_visibility="collapsed"
            )
            
            if selected_email_drill:
                drill_row = week_full_df[week_full_df["email"] == selected_email_drill].iloc[0]
                
                # Map state color codes
                status_colors = {
                    "Struggling / Concern": ("#b91c1c", "#fde8e8"),
                    "QA Quality Concern": ("#9a3412", "#ffedd5"),
                    "Mixed Performance": ("#d97706", "#ffeedd"),
                    "Solid / Baseline Met": ("#0c8599", "#e6fcf5"),
                    "Excelling / High Growth": ("#2b8a3e", "#ebfbee"),
                    "Incomplete Metrics": ("#4b5563", "#f3f4f6"),
                }
                s_color, s_bg = status_colors.get(drill_row["hr_status"], ("#4b5563", "#f3f4f6"))
                
                st.markdown(f"""
                <div class="detail-card" style="border-left: 6px solid {s_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 0.75rem;">
                        <div style="font-size: 1.25rem; font-weight: 800; color: #1e293b;">
                            {name_by_email.get(selected_email_drill, display_name(selected_email_drill))}
                        </div>
                        <span style="font-size: 0.85rem; font-weight: 700; color: {s_color}; background: {s_bg}; padding: 0.3rem 0.8rem; border-radius: 20px; display: inline-flex; align-items: center;">
                            {drill_row["hr_emoji"]} {drill_row["hr_status"]}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Compact responses rendering
                col_ach, col_cha, col_hi = st.columns(3)
                with col_ach:
                    st.markdown('<div class="detail-section-title">Key Achievements</div>', unsafe_allow_html=True)
                    ach = str(drill_row.get("key_achievements", "") or "").strip()
                    st.markdown(f'<div class="answer-box">{ach if ach else "*(No achievements shared)*"}</div>', unsafe_allow_html=True)
                with col_cha:
                    st.markdown('<div class="detail-section-title">Challenges Faced</div>', unsafe_allow_html=True)
                    cha = str(drill_row.get("challenges", "") or "").strip()
                    st.markdown(f'<div class="answer-box">{cha if cha else "*(No challenges shared)*"}</div>', unsafe_allow_html=True)
                with col_hi:
                    st.markdown('<div class="detail-section-title">Other Highlights</div>', unsafe_allow_html=True)
                    hi = str(drill_row.get("other_highlights", "") or "").strip()
                    st.markdown(f'<div class="answer-box">{hi if hi else "*(No highlights shared)*"}</div>', unsafe_allow_html=True)
                    
                # Quick Stats Row
                col1, col2, col3 = st.columns(3)
                with col1:
                    met = drill_row.get("met_expectations")
                    st.metric("Met Employer Expectations", str(met) if pd.notna(met) else "N/A")
                with col2:
                    completed = drill_row.get("tickets_completed")
                    expected = drill_row.get("tickets_expected")
                    tickets_val = f"{int(completed)} / {int(expected)}" if pd.notna(completed) and pd.notna(expected) else "N/A"
                    st.metric("Tickets Completed vs Expected", tickets_val)
                with col3:
                    qa = drill_row.get("qa_first_pass_pct")
                    qa_val = f"{qa:.0f}%" if pd.notna(qa) else "N/A"
                    st.metric("First-Pass QA %", qa_val)

# --- VIEW: TALENT PROFILES ---
elif view_mode == "Talent Profiles":
    # Sidebar Profile selection grouped by Client
    with st.sidebar:
        st.subheader("Select Talent Profile")
        
        # Build client-talent mappings dynamically
        talent_to_client = {e: TALENT_ROSTER[e]["client"] for e in people}
        client_to_talents = {}
        for e in people:
            c = talent_to_client[e]
            client_to_talents.setdefault(c, []).append(e)
            
        clients = sorted(list(client_to_talents.keys()))
        
        # Determine currently selected talent
        curr_talent = st.session_state.selected_talent
        if curr_talent not in people:
            curr_talent = people[0]
            st.session_state.selected_talent = curr_talent
            
        curr_client = talent_to_client[curr_talent]
        
        # Track selected client in session state
        if "selected_client" not in st.session_state or st.session_state.selected_client not in clients:
            st.session_state.selected_client = curr_client

        # Select Client / Project using modern pills
        selected_client = st.pills(
            "Client / Project",
            clients,
            selection_mode="single",
            default=st.session_state.selected_client,
            key="client_pill"
        )
        if not selected_client:
            selected_client = st.session_state.selected_client
        else:
            st.session_state.selected_client = selected_client
            
        # Filter talents for the selected client
        client_talents = client_to_talents[selected_client]
        
        # Ensure currently selected talent is within the selected client's talents
        if st.session_state.selected_talent not in client_talents:
            st.session_state.selected_talent = client_talents[0]
            
        # Select Talent using modern pills
        selected_talent = st.pills(
            "Select Talent",
            client_talents,
            selection_mode="single",
            default=st.session_state.selected_talent,
            format_func=lambda e: name_by_email[e],
            key="talent_pill"
        )
        if not selected_talent:
            selected_talent = st.session_state.selected_talent
        else:
            st.session_state.selected_talent = selected_talent
            
        selected = st.session_state.selected_talent
        
    weeks_df = person_weeks(df, selected)
    talent_name = name_by_email[selected]
    
    st.title(f"👤 {talent_name}")
    st.caption(f"{len(weeks_df)} weekly check-in logs submitted")
    
    progress_rows = []
    # Find this talent's first-ever submission week to avoid blank leading rows
    first_talent_week = weeks_df["week"].dropna().min() if not weeks_df.empty else None
    # Loop over unique weeks chronologically, starting from their first submission
    for w in unique_weeks:
        # Skip weeks before this talent ever submitted
        if first_talent_week and w < first_talent_week:
            continue
        talent_week_rows = weeks_df[weeks_df["week"] == w] if not weeks_df.empty else pd.DataFrame()
        
        # Format the week beginning date label (e.g. Monday's date)
        start_date_str = w.split("/")[0]
        try:
            start_dt = pd.to_datetime(start_date_str)
            week_begin_lbl = start_dt.strftime("%d %b %Y")
        except Exception:
            week_begin_lbl = w
            
        if not talent_week_rows.empty:
            # Submission exists!
            row = talent_week_rows.iloc[0]
            ts = row.get("timestamp")
            ts_val = ts.strftime("%d/%m/%Y %H:%M:%S") if pd.notna(ts) else ""
            
            completed = row.get("tickets_completed")
            completed_val = str(int(completed)) if pd.notna(completed) else ""
            
            expected = row.get("tickets_expected")
            expected_val = str(int(expected)) if pd.notna(expected) else ""
            
            qa = row.get("qa_first_pass_pct")
            qa_val = f"{int(qa)}%" if pd.notna(qa) else ""
            
            rating = row.get("overall_rating")
            rating_val = str(int(rating)) if pd.notna(rating) else ""
            
            progress_rows.append({
                "Week Beginning": week_begin_lbl,
                "Timestamp": ts_val,
                "Email address": row.get("email", ""),
                "What were your key achievements of the week?": row.get("key_achievements", ""),
                "Number of tickets actually completed QA or Done?": completed_val,
                "Expected number of tickets to get completed": expected_val,
                "% of tickets that passed QA on first attempt": qa_val,
                "What were your challenges of the week?": row.get("challenges", ""),
                "Have you met all the expectations of your employer for this week?": row.get("met_expectations", ""),
                "Overall rating of your performance this week?": rating_val,
                "Write here any other things you want to highlight (optional)": row.get("other_highlights", ""),
                "Upload any image or document you want us to see (optional)": row.get("upload", "")
            })
        else:
            # Missing submission for this week!
            progress_rows.append({
                "Week Beginning": week_begin_lbl,
                "Timestamp": "",
                "Email address": selected,
                "What were your key achievements of the week?": "",
                "Number of tickets actually completed QA or Done?": "",
                "Expected number of tickets to get completed": "",
                "% of tickets that passed QA on first attempt": "",
                "What were your challenges of the week?": "",
                "Have you met all the expectations of your employer for this week?": "",
                "Overall rating of your performance this week?": "",
                "Write here any other things you want to highlight (optional)": "",
                "Upload any image or document you want us to see (optional)": ""
            })
            
    progress_table_df = pd.DataFrame(progress_rows)
    # Build a full-width scrollable HTML table so no columns are cropped
    # Columns that should stay compact (no wrap)
    NOWRAP_COLS = {
        "Week Beginning", "Timestamp", "Email address",
        "Number of tickets actually completed QA or Done?",
        "Expected number of tickets to get completed",
        "% of tickets that passed QA on first attempt",
        "Overall rating of your performance this week?",
        "Have you met all the expectations of your employer for this week?",
    }
    def _df_to_html_table(df):
        header_cells = "".join(
            f'<th style="padding:10px 14px;white-space:nowrap;background:#585ba6;color:white;'
            f'font-weight:600;font-size:0.82rem;text-align:left;border-bottom:2px solid #464999;">'
            f'{col}</th>' for col in df.columns
        )
        rows_html = ""
        for i, (_, row) in enumerate(df.iterrows()):
            bg = "#f8f7ff" if i % 2 == 0 else "white"
            cells = ""
            for col, val in zip(df.columns, row.values):
                if col in NOWRAP_COLS:
                    cell_style = (
                        "padding:9px 14px;white-space:nowrap;font-size:0.82rem;"
                        "color:#334155;border-bottom:1px solid #e8e6ff;"
                    )
                else:
                    cell_style = (
                        "padding:9px 14px;white-space:normal;word-break:break-word;"
                        "font-size:0.82rem;color:#334155;border-bottom:1px solid #e8e6ff;"
                        "max-width:380px;min-width:180px;"
                    )
                cells += f'<td style="{cell_style}">{val}</td>'
            rows_html += f'<tr style="background:{bg}">{cells}</tr>'
        return (
            '<div style="overflow-x:auto;border-radius:12px;border:1px solid #d8d6f0;'
            'box-shadow:0 4px 16px rgba(88,91,166,0.10);margin:1rem 0;">'
            f'<table style="border-collapse:collapse;width:max-content;min-width:100%;font-family:inherit;">'
            f'<thead><tr>{header_cells}</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table></div>'
        )
    # ── Growth Overview (above the table) ─────────────────────────────────
    if not weeks_df.empty:
        st.markdown(
            '<p style="font-size:1.25rem;font-weight:700;color:#585ba6;margin-bottom:4px;">'
            'Growth Overview</p>'
            '<p style="font-size:0.85rem;color:#7b7fa8;margin-top:0;">Week-by-week trend across all submissions</p>',
            unsafe_allow_html=True
        )

        def _safe_float(val):
            import math
            try:
                f = float(val)
                return None if math.isnan(f) else f
            except (TypeError, ValueError):
                return None

        # Build trend dataframe chronologically (oldest → newest)
        trend_rows = []
        for _, r in weeks_df.iterrows():
            week_str = str(r.get("week", ""))
            # Parse the start date from the week range string e.g. "2026-03-10/2026-03-16"
            start_part = week_str.split("/")[0].strip()
            try:
                week_dt = pd.to_datetime(start_part)
            except Exception:
                week_dt = None
            trend_rows.append({
                "Date": week_dt,
                "Tickets Done": _safe_float(r.get("tickets_completed")),
                "Tickets Expected": _safe_float(r.get("tickets_expected")),
                "QA First-Pass %": _safe_float(r.get("qa_first_pass_pct")),
            })
        trend_df = (
            pd.DataFrame(trend_rows)
            .dropna(subset=["Date"])
            .sort_values("Date", ascending=True)
            .set_index("Date")
        )

        if len(trend_df) >= 1:
            latest = trend_df.iloc[-1]
            prev   = trend_df.iloc[-2] if len(trend_df) >= 2 else None

            def _delta_html(curr, prior, suffix="", higher_is_better=True):
                if curr is None:
                    return '<span style="color:#aaa">N/A</span>'
                if prior is None or prior == curr:
                    return f'<span style="color:#585ba6;font-weight:700">{(curr or 0):.1f}{suffix}</span>'
                delta = curr - prior
                color = "#22c55e" if (delta > 0) == higher_is_better else "#ef4444"
                arrow = "▲" if delta > 0 else "▼"
                return (
                    f'<span style="color:#1e3b70;font-weight:700;font-size:1.4rem">{curr:.1f}{suffix}</span> '
                    f'<span style="color:{color};font-size:0.85rem">{arrow} {abs(delta):.1f}{suffix} vs prev week</span>'
                )

            card_style = (
                "background:linear-gradient(135deg,#f3f2ff 0%,#ebe9ff 100%);"
                "border:1px solid #c7c5f0;border-radius:14px;padding:18px 20px;"
                "box-shadow:0 4px 16px rgba(88,91,166,0.10);"
            )
            c1, c2 = st.columns(2)
            with c1:
                t_curr = latest.get("Tickets Done")
                t_prev = prev.get("Tickets Done") if prev is not None else None
                st.markdown(
                    f'<div style="{card_style}">'
                    f'<div style="color:#585ba6;font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Tickets Done</div>'
                    f'<div style="margin-top:8px">{_delta_html(t_curr, t_prev)}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            with c2:
                q_curr = latest.get("QA First-Pass %")
                q_prev = prev.get("QA First-Pass %") if prev is not None else None
                st.markdown(
                    f'<div style="{card_style}">'
                    f'<div style="color:#585ba6;font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;">QA First-Pass</div>'
                    f'<div style="margin-top:8px">{_delta_html(q_curr, q_prev, "%")}</div>'
                    f'</div>', unsafe_allow_html=True
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            if len(trend_df) >= 2:
                tab_tickets, tab_qa = st.tabs(["Tickets Done vs Expected", "QA First-Pass %"])
                with tab_tickets:
                    tickets_series = trend_df[["Tickets Done", "Tickets Expected"]].dropna(how="all")
                    if not tickets_series.empty:
                        st.line_chart(
                            tickets_series,
                            color=["#585ba6", "#c4b5fd"],
                            height=220,
                            use_container_width=True,
                        )
                    else:
                        st.caption("No ticket data available.")
                with tab_qa:
                    qa_series = trend_df[["QA First-Pass %"]].dropna()
                    if not qa_series.empty:
                        st.line_chart(
                            qa_series,
                            color="#4f46e5",
                            height=220,
                            use_container_width=True,
                        )
                    else:
                        st.caption("No QA data available.")

        st.markdown("---")

    # ── Gemini AI Talent Coach Section ────────────────────────────────────
    if not weeks_df.empty:
        st.markdown(
            '<p style="font-size:1.25rem;font-weight:700;color:#585ba6;margin-bottom:4px;margin-top:1.5rem;">'
            '🤖 AI Talent Coach Insights</p>'
            '<p style="font-size:0.85rem;color:#7b7fa8;margin-top:0;">Generative AI-powered analysis of weekly performance logs</p>',
            unsafe_allow_html=True
        )
        
        # Check for GEMINI_API_KEY
        gemini_key = get_secret("GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        
        # Allow manual override in session state
        if "gemini_api_key_override" not in st.session_state:
            st.session_state.gemini_api_key_override = ""
            
        active_key = st.session_state.gemini_api_key_override or gemini_key
        
        with st.expander("✨ Open AI Talent Coach Console", expanded=False):
            if not active_key:
                st.info("🔑 **Unlock AI Coaching Insights!** Get a free Gemini API key to start.")
                st.markdown(
                    "1. Go to [Google AI Studio](https://aistudio.google.com/) and click **Get API key**.\n"
                    "2. Create a free API key in seconds.\n"
                    "3. Paste your key below to unlock this feature on this session:"
                )
                input_key = st.text_input("Gemini API Key", type="password", key="key_input_field")
                if input_key:
                    st.session_state.gemini_api_key_override = input_key
                    st.success("API Key updated for this session!")
                    st.rerun()
            else:
                # We have a key!
                st.markdown("##### 🧠 Performance Analysis & Actionable Advice")
                
                # Button to trigger AI generation
                if f"ai_summary_{selected}" not in st.session_state:
                    st.session_state[f"ai_summary_{selected}"] = None
                    
                generate_btn = st.button("🪄 Generate AI Assessment", type="primary", use_container_width=True)
                
                if generate_btn or st.session_state[f"ai_summary_{selected}"]:
                    if generate_btn:
                        # Show spinner
                        with st.spinner("Analyzing talent logs with Gemini..."):
                            try:
                                # 1. Prepare data for the prompt
                                recent_submissions = weeks_df.head(4) # Analyze last 4 submissions
                                if recent_submissions.empty:
                                    st.warning("No submission history to analyze.")
                                else:
                                    import google.generativeai as genai
                                    genai.configure(api_key=active_key)
                                    
                                    # Format history for prompt
                                    history_text = ""
                                    for idx, (_, r) in enumerate(recent_submissions.iterrows()):
                                        week_lbl = format_week_label(r)
                                        ach = r.get("key_achievements", "N/A")
                                        chall = r.get("challenges", "N/A")
                                        comp = r.get("tickets_completed", "N/A")
                                        exp = r.get("tickets_expected", "N/A")
                                        qa = r.get("qa_first_pass_pct", "N/A")
                                        rat = r.get("overall_rating", "N/A")
                                        tier = r.get("growth_tier", "N/A")
                                        
                                        history_text += (
                                            f"### Week Beginning: {week_lbl}\n"
                                            f"- **Growth Tier**: {tier}\n"
                                            f"- **Tickets Completed**: {comp} / {exp}\n"
                                            f"- **QA First-Pass %**: {qa}%\n"
                                            f"- **Self-Rating**: {rat} / 5\n"
                                            f"- **Key Achievements**: {ach}\n"
                                            f"- **Challenges**: {chall}\n\n"
                                        )
                                        
                                    prompt = (
                                        f"You are an expert HR Talent Specialist and Agile Performance Coach. "
                                        f"You are analyzing the performance of a software talent named {talent_name} based on their last {len(recent_submissions)} weeks of self-reported check-ins.\n\n"
                                        f"Here is their performance history:\n"
                                        f"{history_text}\n"
                                        f"Based on this data, provide a professional, constructive, and actionable assessment including:\n"
                                        f"1. **Executive Performance Summary**: A brief, encouraging 3-4 sentence paragraph summarizing their recent progress, work rate, and highlights.\n"
                                        f"2. **Risk & Trajectory Assessment**: Identify any warning signs (such as a drop in tickets, low QA first-pass, repetitive achievements, or signs of 'Silent Struggle' or plateauing). Be objective.\n"
                                        f"3. **Tailored Manager Coaching Tips**: Give 3 highly practical, specific coaching points or questions for the manager to use in their next 1-on-1 with {talent_name} to help them grow and level up.\n\n"
                                        f"Formatting Guidelines: Use clear markdown headers, bold bullet points, and maintain a supportive but professional corporate tone. Keep the advice tailored specifically to the metrics and text they wrote."
                                    )
                                    
                                    # Call Gemini API
                                    model = genai.GenerativeModel("gemini-1.5-flash")
                                    response = model.generate_content(prompt)
                                    st.session_state[f"ai_summary_{selected}"] = response.text
                            except Exception as ex:
                                st.error(f"Gemini API Error: {ex}")
                                st.info("Tip: Double-check your API key and network connection.")
                                
                    # Display the cached or newly generated summary
                    if st.session_state[f"ai_summary_{selected}"]:
                        st.markdown(
                            '<div style="background-color:#f8fafc; border-left: 4px solid #585ba6; '
                            'padding: 1.5rem; border-radius: 8px; margin: 1rem 0; box-shadow: 0 4px 10px rgba(0,0,0,0.02);">'
                            f'{st.session_state[f"ai_summary_{selected}"]}'
                            '</div>',
                            unsafe_allow_html=True
                        )
        st.markdown("---")

    # ── Chronological Progress Table ────────────────────────────────────────
    st.subheader("Chronological Progress History")
    st.caption("A consolidated timeline of metrics and weekly check-in entries across all weeks.")
    st.markdown(_df_to_html_table(progress_table_df), unsafe_allow_html=True)

    if not weeks_df.empty:
        # --- Person-level aggregate summary checks ---
        st.markdown("---")
        summary = person_summary_checks(weeks_df)
        if summary:
            st.subheader("At a glance")
            for c in summary:
                _render_check(c)
            st.markdown("---")
                    
        # --- 3. Full Deep Logs (Newest First) ---
        st.markdown("---")
        st.subheader("Detailed Weekly Submissions")

        for i, (_, row) in enumerate(weeks_df.iterrows()):
            prior = weeks_df.iloc[i + 1] if i + 1 < len(weeks_df) else None

            checks = week_checks(row, prior)
            warn_count = sum(1 for c in checks if c.status == "warn")

            week_label = format_week_label(row)
            warn_badge = f"  {warn_count} item(s) need attention" if warn_count else ""
            expander_label = f"Week of {week_label}{warn_badge}"

            # Most recent week open by default, rest collapsed
            with st.expander(expander_label, expanded=(i == 0)):
                for c in checks:
                    _render_check(c)

                st.markdown("**What they wrote**")
                for col, label in [
                    ("key_achievements", "Key achievements"),
                    ("challenges", "Challenges"),
                    ("other_highlights", "Other highlights"),
                ]:
                    val = str(row.get(col, "") or "").strip()
                    if val:
                        st.markdown(f"*{label}*")
                        st.write(val)

                nums = []
                if pd.notna(row.get("tickets_completed")):
                    nums.append(f"Tickets done: **{int(row['tickets_completed'])}**")
                if pd.notna(row.get("tickets_expected")):
                    nums.append(f"Expected: **{int(row['tickets_expected'])}**")
                if pd.notna(row.get("qa_first_pass_pct")):
                    nums.append(f"QA first-pass: **{row['qa_first_pass_pct']:.0f}%**")
                if pd.notna(row.get("overall_rating")):
                    nums.append(f"Self-rating: **{int(row['overall_rating'])}/5**")
                if pd.notna(row.get("met_expectations")) and str(row["met_expectations"]).strip():
                    nums.append(f"Met expectations: **{row['met_expectations']}**")
                if nums:
                    st.markdown(" · ".join(nums))
    else:
        st.info("No detailed check-in submissions have been submitted by this talent yet.")
