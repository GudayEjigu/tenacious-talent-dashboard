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

# --- Dynamic Google Doc Roster Parser ---
def guess_email(name: str) -> str:
    clean = name.strip().lower()
    if "arun" in clean: return "arun@gettenacious.com"
    if "yabebal" in clean: return "yabebal@gettenacious.com"
    if "bereket" in clean: return "bereket@gettenacious.com"
    if "bezawit" in clean: return "bezawit@gettenacious.com"
    if "guday" in clean: return "guday@gettenacious.com"
    if "maureen" in clean: return "maureen@gettenacious.com"
    
    # Technical team
    if "nabil" in clean: return "nabil@gettenacious.com"
    if "yosef" in clean: return "yosef@gettenacious.com"
    if "dibora" in clean: return "dibora@gettenacious.com"
    if "jabez" in clean: return "jabez@gettenacious.com"
    if "rahel" in clean: return "rahel@gettenacious.com"
    if "milky" in clean: return "milky@gettenacious.com"
    if "mahlet" in clean: return "mahlet@gettenacious.com"
    if "rediet" in clean: return "rediet@gettenacious.com"
    if "yohanes teshome" in clean: return "yohanes@gettenacious.com"
    if "daniel" in clean: return "daniel@gettenacious.com"
    if "nahom habtamu" in clean or "nahom habt" in clean: return "nahom@gettenacious.com"
    if "nahom bekele" in clean: return "nahomb@gettenacious.com"
    if "zelalem" in clean: return "zelalem@gettenacious.com"
    if "belay" in clean: return "belay@gettenacious.com"
    if "birhanu" in clean: return "birhanu@gettenacious.com"
    if "mama" in clean: return "mama@gettenacious.com"
    if "samuel" in clean: return "samuel@gettenacious.com"
    if "nardos" in clean: return "nardos@gettenacious.com"
    if "lillian" in clean: return "lillian@gettenacious.com"
    if "nebiyou" in clean: return "nebiyou@gettenacious.com"
    if "dereje" in clean: return "dereje@gettenacious.com"
    if "alazar" in clean: return "alazar@gettenacious.com"
    if "miliyon" in clean: return "miliyon@gettenacious.com"
    if "meron" in clean: return "meron@gettenacious.com"
    if "fikerte" in clean: return "fikerte@gettenacious.com"
    if "tesfaye" in clean: return "tesfaye@gettenacious.com"
    if "yohans samuel" in clean: return "yohans@gettenacious.com"
    if "akubazgi" in clean: return "akubazgi@gettenacious.com"
    if "filimon" in clean: return "filimon@gettenacious.com"
    if "sumeya" in clean: return "sumeya@gettenacious.com"
    if "tadesse" in clean: return "tadesse@gettenacious.com"
    if "ekram" in clean: return "ekram@gettenacious.com"
    if "estifanos" in clean: return "estifanos@gettenacious.com"
    
    parts = clean.split()
    first = parts[0] if parts else "unknown"
    return f"{first}@gettenacious.com"

@st.cache_data(ttl=600, show_spinner="Fetching latest roster from Google Doc…")
def load_roster_from_gdoc() -> tuple[dict, list]:
    fallback_roster = {
        "nabil@gettenacious.com": {"name": "Nabil Seid", "client": "Ozone"},
        "yosef@gettenacious.com": {"name": "Yosef Engdawork", "client": "Ozone"},
        "dibora@gettenacious.com": {"name": "Dibora Haile", "client": "Ozone"},
        "jabez@gettenacious.com": {"name": "Jabez Kassa", "client": "Ozone"},
        "rahel@gettenacious.com": {"name": "Rahel Weldegebriel", "client": "Ozone"},
        "milky@gettenacious.com": {"name": "Milky Bekele", "client": "Ozone"},
        "mahlet@gettenacious.com": {"name": "Mahlet Taye", "client": "Ozone"},
        "rediet@gettenacious.com": {"name": "Rediet Girma", "client": "Ozone"},
        "yohanes@gettenacious.com": {"name": "Yohanes Teshome", "client": "Ozone"},
        "daniel@gettenacious.com": {"name": "Daniel Zelalem", "client": "Ozone"},
        "nahom@gettenacious.com": {"name": "Nahom Habtamu", "client": "Computrition"},
        "nahom.fix@gmail.com": {"name": "Nahom Habtamu", "client": "Computrition"},
        "zelalem@gettenacious.com": {"name": "Zelalem Getahun", "client": "Computrition"},
        "belay@gettenacious.com": {"name": "Belay Birhanu", "client": "Computrition"},
        "belay@10academy.org": {"name": "Belay Birhanu", "client": "Computrition"},
        "birhanu@gettenacious.com": {"name": "Birhanu Gudisa", "client": "Computrition"},
        "nahomb@gettenacious.com": {"name": "Nahom Bekele", "client": "Computrition"},
        "mama@gettenacious.com": {"name": "Mama Mohammed", "client": "Computrition"},
        "mamamohammed31@gmail.com": {"name": "Mama Mohammed", "client": "Computrition"},
        "samuel@gettenacious.com": {"name": "Samuel Negash", "client": "RewardOps"},
        "smlnegash@gmail.com": {"name": "Samuel Negash", "client": "RewardOps"},
        "nardos@gettenacious.com": {"name": "Nardos Tilahun", "client": "RewardOps"},
        "lillian@gettenacious.com": {"name": "Lillian Alehegn", "client": "RewardOps"},
        "lillianalehegn123@gmail.com": {"name": "Lillian Alehegn", "client": "RewardOps"},
        "nebiyou@gettenacious.com": {"name": "Nebiyou Belaineh", "client": "RewardOps"},
        "dereje@gettenacious.com": {"name": "Dereje Derib", "client": "RewardOps"},
        "alazar@gettenacious.com": {"name": "Alazar Getachew", "client": "Vanson Technology Services"},
        "alazar.getachew@coraloyalty.com": {"name": "Alazar Getachew", "client": "Vanson Technology Services"},
        "miliyon@gettenacious.com": {"name": "Miliyon Ayalew", "client": "Vanson Technology Services"},
        "meron@gettenacious.com": {"name": "Meron Abdo", "client": "Modo Yoga"},
        "meronabdo954@gmail.com": {"name": "Meron Abdo", "client": "Modo Yoga"},
        "fikerte@gettenacious.com": {"name": "Fikerte Alemayehu", "client": "MIR Digital"},
        "tesfaye@gettenacious.com": {"name": "Tesfaye Alemayehu", "client": "Shega"},
        "yohans@gettenacious.com": {"name": "Yohans Samuel", "client": "Navigate"},
        "akubazgi@gettenacious.com": {"name": "Akubazgi Gebremariam", "client": "SCG"},
        "filimon@gettenacious.com": {"name": "Filimon Haylemariam", "client": "Carlson"},
        "sumeya@gettenacious.com": {"name": "Sumeya Sirmula", "client": "Tech"},
        "tadesse@gettenacious.com": {"name": "Tadesse Abateneh Walelign", "client": "Modo"},
        "ekram@gettenacious.com": {"name": "Ekram Kumdin", "client": "Modo"},
        "estifanos@gettenacious.com": {"name": "Estifanos Teklay", "client": "Modo"},
    }
    
@st.cache_data(ttl=600, show_spinner=False)
def load_milestones_data_v2() -> pd.DataFrame:
    url = "https://docs.google.com/spreadsheets/d/1kFT1zlQwPfQ8cdz_Vop51ZCPjOgiXYrOv8xbn0J8dRc/export?format=csv&gid=1924842637"
    try:
        df = pd.read_csv(url)
        # Normalize column names by stripping trailing whitespace
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"Error fetching milestones: {e}")
        return pd.DataFrame()

def load_roster_from_gdoc():
    fallback_leadership = [
        {"name": "Arun Sharma", "role": "Co-founder", "email": "arun@gettenacious.com"},
        {"name": "Yabebal Fantaye", "role": "Co-founder", "email": "yabebal@gettenacious.com"},
        {"name": "Bereket Kibru", "role": "Technical Client Delivery Manager", "email": "bereket@gettenacious.com"},
        {"name": "Bezawit Wondwosen", "role": "Project Manager", "email": "bezawit@gettenacious.com"},
        {"name": "Guday Berhanu", "role": "Talent Manager", "email": "guday@gettenacious.com"},
        {"name": "Tesfaye Alemayehu", "role": "Tenacious Internal Tech Team", "email": "tesfaye@gettenacious.com"},
        {"name": "Maureen Kiprono", "role": "Finance Manager", "email": "maureen@gettenacious.com"},
    ]
    
    parsed_roster = {}
    aliases = {}
    try:
        m_df = load_milestones_data_v2()
        if not m_df.empty and "Email" in m_df.columns:
            current_name = "Unknown"
            current_client = "Unassigned"
            primary_email = None
            
            for _, row in m_df.iterrows():
                name_val = str(row.get("Name", "")).strip()
                if name_val and name_val.lower() != "nan":
                    current_name = name_val
                    client_val = str(row.get("Client", "")).strip()
                    if client_val and client_val.lower() != "nan":
                        current_client = client_val
                    primary_email = None
                
                email_val = str(row.get("Email", "")).strip().lower()
                if email_val and email_val != "nan":
                    if not primary_email:
                        primary_email = email_val
                        parsed_roster[primary_email] = {
                            "name": current_name, 
                            "client": current_client,
                            "emails": [email_val]
                        }
                    else:
                        aliases[email_val] = primary_email
                        parsed_roster[primary_email]["emails"].append(email_val)
                        
        if parsed_roster:
            return parsed_roster, fallback_leadership, aliases
    except Exception as e:
        print(f"Error loading roster from milestones: {e}")
        
    return fallback_roster, fallback_leadership, {}

# Execute dynamically at startup to populate imported weekly_checks.TALENT_ROSTER
GLOBAL_ALIASES = {}
try:
    gdoc_roster, leadership_contacts, gdoc_aliases = load_roster_from_gdoc()
    TALENT_ROSTER.clear()
    TALENT_ROSTER.update(gdoc_roster)
    GLOBAL_ALIASES.update(gdoc_aliases)
except Exception:
    leadership_contacts = [
        {"name": "Arun Sharma", "role": "Co-founder", "email": "arun@gettenacious.com"},
        {"name": "Yabebal Fantaye", "role": "Co-founder", "email": "yabebal@gettenacious.com"},
        {"name": "Bereket Kibru", "role": "Technical Client Delivery Manager", "email": "bereket@gettenacious.com"},
        {"name": "Bezawit Wondwosen", "role": "Project Manager", "email": "bezawit@gettenacious.com"},
        {"name": "Guday Berhanu", "role": "Talent Manager", "email": "guday@gettenacious.com"},
        {"name": "Tesfaye Alemayehu", "role": "Tenacious Internal Tech Team", "email": "tesfaye@gettenacious.com"},
        {"name": "Maureen Kiprono", "role": "Finance Manager", "email": "maureen@gettenacious.com"},
    ]

st.set_page_config(
    page_title="Talent management weekly overview",
    page_icon="icon.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Styling & CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stMarkdownContainer"], button, input, select, textarea, table, td, th, p, h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    h1, h1 *, div[data-testid="stMarkdownContainer"] h1, div[data-testid="stHeadingWithActionElements"] h1, div[data-testid="stMarkdownContainer"] h1 * {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #1e293b !important;
        margin-bottom: 0.2rem !important;
        letter-spacing: -0.02em !important;
        line-height: 1.2 !important;
    }
    h2, h2 *, div[data-testid="stMarkdownContainer"] h2, div[data-testid="stHeadingWithActionElements"] h2, div[data-testid="stMarkdownContainer"] h2 * {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        margin-top: 1.2rem !important;
        margin-bottom: 0.6rem !important;
        letter-spacing: -0.01em !important;
        line-height: 1.3 !important;
    }
    h3, h3 *, div[data-testid="stMarkdownContainer"] h3, div[data-testid="stHeadingWithActionElements"] h3, div[data-testid="stMarkdownContainer"] h3 * {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
        margin-top: 0.6rem !important;
        margin-bottom: 0.3rem !important;
    }
    h4, h4 *, [data-testid="stHeader"] h4 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }

    @media (max-width: 768px) {
        h1, h1 *, div[data-testid="stMarkdownContainer"] h1, div[data-testid="stHeadingWithActionElements"] h1, div[data-testid="stMarkdownContainer"] h1 * {
            font-size: 2rem !important;
        }
        h2, h2 *, div[data-testid="stMarkdownContainer"] h2, div[data-testid="stHeadingWithActionElements"] h2, div[data-testid="stMarkdownContainer"] h2 * {
            font-size: 1.75rem !important;
        }
        h3, h3 *, div[data-testid="stMarkdownContainer"] h3, div[data-testid="stHeadingWithActionElements"] h3, div[data-testid="stMarkdownContainer"] h3 * {
            font-size: 1.25rem !important;
        }
        h4, h4 *, [data-testid="stHeader"] h4 {
            font-size: 1.125rem !important;
        }
    }
    p, span, li, td, th, div, a {
        font-size: 0.74rem !important;
    }
    .stMarkdown caption, [data-testid="stMarkdownContainer"] caption, label {
        font-size: 0.72rem !important;
    }

    .main, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"] {
        background-color: #ffffff !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(8px) !important;
    }

    /* Prevent icon fonts from being overridden by Montserrat */
    [data-testid="stIconMaterial"], .material-icons, [class*="Icon"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    }

    /* Original check-in badges converted to transparent list bullets */
    .check-ok   { padding: 3px 0 !important; margin: 1px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.8rem !important; }
    .check-warn { padding: 3px 0 !important; margin: 1px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.8rem !important; }
    .check-watch{ padding: 3px 0 !important; margin: 1px 0 !important; background: transparent !important; color: #334155 !important; font-size: 0.8rem !important; }
    .week-head  { font-size: 1.05rem; font-weight: 700; margin: 0.8rem 0 0.4rem 0; }
    .answer-box { background: #f8f9fa; padding: 0.6rem 0.8rem; border-radius: 8px;
                  margin: 0.3rem 0 0.6rem 0; white-space: pre-wrap; font-size: 0.8rem; color: #334155; }
                  
    /* HR Row container styles */
    .hr-row {
        display: flex;
        align-items: center;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
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
        font-size: 0.88rem;
        color: #1e293b;
    }
    .email-text {
        font-size: 0.72rem;
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
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.25rem 0.6rem;
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
        min-width: 260px !important;
        max-width: 260px !important;
        width: 260px !important;
        height: 100vh !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem !important; /* Move logo and content to the absolute top */
    }
    [data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important; /* Move logo and content to the absolute top */
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
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.4rem !important;
    }
    /* Sidebar Flat Navigation Buttons - base layout */
    [data-testid="stSidebar"] [data-testid="stButton"] button {
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        text-align: left !important;
        padding: 0.55rem 0.85rem !important; /* Slight padding inside button */
        width: 100% !important;
        color: #64748b !important; /* Slate/gray text */
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        box-shadow: none !important;
        transition: background 0.15s, color 0.15s !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important; /* Center vertically */
        gap: 8px !important; /* Small gap between icon and text */
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background-color: #f1f5f9 !important; /* Subtle light gray hover background */
        color: #1e293b !important;
        transform: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] button p,
    [data-testid="stSidebar"] [data-testid="stButton"] button span,
    [data-testid="stSidebar"] [data-testid="stButton"] button div {
        color: inherit !important;
        font-weight: inherit !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important; /* Vertically center icon and text */
        gap: 8px !important; /* Flex gap */
        margin: 0 !important;
        padding: 0 !important;
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
        unsafe_allow_html=True
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
        
        # Map known secondary aliases from the Google Sheet
        raw_df["email"] = raw_df["email"].replace(GLOBAL_ALIASES)
        
        # Fuzzy match unrecognized Telegram bot aliases by first name
        new_aliases = {}
        for email in raw_df["email"].dropna().unique():
            if email not in TALENT_ROSTER:
                local_part = email.split("@")[0]
                for primary_email, info in TALENT_ROSTER.items():
                    name_parts = info["name"].lower().split()
                    if name_parts and (local_part == name_parts[0] or local_part in name_parts):
                        new_aliases[email] = primary_email
                        break
                        
        if new_aliases:
            raw_df["email"] = raw_df["email"].replace(new_aliases)

        # Filter strictly to active talents from the roster (drops inactive)
        raw_df = raw_df[raw_df["email"].isin(TALENT_ROSTER.keys())]

    
    # Process weekly signals & longitudinal alerts
    df_engine = growth_signal_engine.process_dataframe(raw_df)
    df_engine["spec_growth_tier"] = df_engine["growth_tier"]
    
    # Add numerical metrics for reason compiling
    df_scored = scoring.enrich_dataframe(df_engine.drop(columns=["growth_tier"]))
    df_scored["growth_tier"] = df_scored["spec_growth_tier"]
    
    return df_scored, parse_info
def format_tenure(months_str: str) -> str:
    if not months_str or str(months_str).lower() == "nan":
        return "--"
    try:
        m = float(months_str)
        if m < 0:
            return "--"
        total_months = int(m)
        if total_months < 12:
            return f"{total_months} months"
        years = total_months // 12
        rem_months = total_months % 12
        y_str = f"{years} year{'s' if years > 1 else ''}"
        m_str = f" {rem_months} month{'s' if rem_months > 1 else ''}" if rem_months > 0 else ""
        return y_str + m_str
    except ValueError:
        return str(months_str)


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
    st.title("Tenacious Growth Dashboard")
    st.markdown("### Welcome! Let's connect your weekly check-in data.")
    st.info(
        "To get started, you can either **upload a CSV export** of your Google Sheet directly, "
        "or **paste a shared Google Sheets link**."
    )
    
    tab_upload, tab_link = st.tabs(["Upload CSV File (Private & Local)", "Link Google Sheet"])
    
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
                st.success("CSV uploaded and parsed successfully!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error parsing uploaded CSV: {ex}")
                
    with tab_link:
        st.markdown("#### Paste your Google Sheet sharing link:")
        st.info(
            "**Important:** Make sure the sheet's general access is set to **'Anyone with the link can view'** "
            "so the dashboard can fetch the data automatically."
        )
        override = st.text_input("Google Sheets Link (shared or published CSV URL)", value=get_secret("sheet_csv_url", ""))
        if override:
            try:
                st.cache_data.clear()
                df_scored, p_info = _load_enriched(override)
                st.session_state.uploaded_df = df_scored
                st.session_state.uploaded_parse_info = p_info
                st.success("Linked to Google Sheet successfully!")
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
_all_people = sorted(list({e for e in TALENT_ROSTER.keys()}))
# Only keep people who have submitted at least once
_submitted_emails = set(df["email"].dropna().unique())
people = _all_people
name_by_email = {e: display_name(e) for e in people}

# Filter valid unique weeks globally so they are available in both views
unique_weeks = sorted(df["week"].dropna().unique().tolist())
unique_weeks = [w for w in unique_weeks if w and str(w) != "NaT"]

# --- Session State Initialization ---
if "view_mode" not in st.session_state or st.session_state.view_mode not in [
    "team_directory",
    "weekly_status",
    "talent_profiles"
]:
    st.session_state.view_mode = "team_directory"
if "selected_talent" not in st.session_state:
    st.session_state.selected_talent = people[0] if people else None

# --- Handle Query Parameters for Navigation ---
if "selected_talent" in st.query_params:
    tgt_talent = st.query_params["selected_talent"]
    if tgt_talent in people:
        st.session_state.selected_talent = tgt_talent
        st.session_state.view_mode = "talent_profiles"
    st.query_params.clear()

# --- Top Navbar (Native Streamlit) ---
view_mode = st.session_state.view_mode

import base64 as _b64
import os as _os
_logo_b64 = ""
try:
    if _os.path.exists("logo.png"):
        _logo_path = "logo.png"
    else:
        _logo_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logo.png")
    with open(_logo_path, "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
except Exception:
    pass

_logo_img = (
    f'<img src="data:image/png;base64,{_logo_b64}" style="height: 56px; width: auto; max-height: 56px; display: block; margin-top: 0px;" alt="Tenacious" />'
    if _logo_b64 else
    '<span style="font-weight:800;font-size:1.4rem;color:#585ba6; line-height: 56px;">Tenacious</span>'
)

# Render sticky navbar using a named container
with st.container(key="top_navbar"):
    col_logo, col_nav1, col_nav2, col_nav3, col_space, col_refresh = st.columns([2.5, 1.4, 1.4, 1.4, 3, 1])
    
    with col_logo:
        st.markdown(_logo_img, unsafe_allow_html=True)
        
    with col_nav1:
        if st.button("Team Directory", key="btn_team_directory", use_container_width=True):
            st.session_state.view_mode = "team_directory"
            st.rerun()
            
    with col_nav2:
        if st.button("Weekly Status", key="btn_weekly_status", use_container_width=True):
            st.session_state.view_mode = "weekly_status"
            st.rerun()
            
    with col_nav3:
        if st.button("Talent Profiles", key="btn_talent_profiles", use_container_width=True):
            st.session_state.view_mode = "talent_profiles"
            st.rerun()
            
    with col_refresh:
        if st.button("⟳ Refresh", key="btn_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# Apply CSS for the sticky navbar and the tab styling
active_btn_key = f"btn_{st.session_state.view_mode}"

st.markdown(
    f"""
    <style>
    /* Make the container sticky at the top */
    div.st-key-top_navbar {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999999 !important;
        background: #ffffff !important;
        border-bottom: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 12px rgba(88,91,166,0.07) !important;
        padding: 0.5rem 2.5rem 0.5rem 2.5rem !important;
        height: 80px !important;
    }}
    
    /* Push main content below fixed navbar */
    [data-testid="stAppViewContainer"] > .main {{
        padding-top: 96px !important;
    }}
    /* Hide Streamlit's default sidebar collapse button if sidebar is visible */
    [data-testid="stSidebarCollapseButton"] {{
        top: 86px !important;
    }}
    /* Hide the Streamlit default top header bar */
    [data-testid="stHeader"] {{
        display: none !important;
    }}
    /* Adjust sidebar top so it starts below the navbar */
    [data-testid="stSidebar"] {{
        top: 80px !important;
        height: calc(100vh - 80px) !important;
    }}
    
    /* Center columns vertically in the navbar */
    div.st-key-top_navbar [data-testid="column"] {{
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    
    /* Style all buttons in the navbar to look like tabs */
    div.st-key-top_navbar button {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 3px solid transparent !important;
        padding: 0.6rem 0.5rem !important;
        font-family: 'Montserrat', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
        min-height: 0 !important;
        height: auto !important;
        box-shadow: none !important;
        transition: color 0.18s, border-color 0.18s !important;
        margin-top: 10px !important;
    }}
    div.st-key-top_navbar button:hover {{
        color: #585ba6 !important;
        border-bottom: 3px solid #e2e8f0 !important;
    }}
    div.st-key-top_navbar button:focus:not(:focus-visible) {{
        color: #64748b !important;
    }}
    div.st-key-top_navbar button p {{
        font-size: 0.95rem !important;
    }}
    
    /* Active tab styling */
    div.st-key-top_navbar div.st-key-{active_btn_key} button {{
        color: #585ba6 !important;
        border-bottom: 3px solid #585ba6 !important;
        font-weight: 700 !important;
    }}
    div.st-key-top_navbar div.st-key-{active_btn_key} button:focus:not(:focus-visible) {{
        color: #585ba6 !important;
    }}
    div.st-key-top_navbar div.st-key-{active_btn_key} button p {{
        font-weight: 700 !important;
    }}
    
    /* Special styling for the refresh button to look like a small action button */
    div.st-key-top_navbar div.st-key-btn_refresh button {{
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
        padding: 0.45rem 1rem !important;
        font-size: 0.85rem !important;
        margin-top: 5px !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }}
    div.st-key-top_navbar div.st-key-btn_refresh button p {{
        font-size: 0.85rem !important;
    }}
    div.st-key-top_navbar div.st-key-btn_refresh button:hover {{
        background: #f1f5f9 !important;
        color: #1e293b !important;
        border-color: #cbd5e1 !important;
        border-bottom: 1px solid #cbd5e1 !important;
    }}
    
    /* Fix markdown margin in the logo column */
    div.st-key-top_navbar [data-testid="stMarkdownContainer"] p {{
        margin-bottom: 0 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar removed as requested ---

# --- VIEW: WEEKLY STATUS BOARD ---
if view_mode == "weekly_status":
        
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
                    cell_html = f'<a href="/?selected_talent={email}" target="_self" class="cell-link" style="color: #1e3a8a !important; font-weight: 600;">{html.escape(name)}</a>'
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
elif view_mode == "talent_profiles":
    st.markdown("### Select Talent Profile")
    
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

    # Render selection pills side-by-side at the top of the profile
    col_client, col_talent = st.columns(2)
    
    with col_client:
        selected_client = st.pills(
            "Filter by Client / Project",
            clients,
            selection_mode="single",
            default=st.session_state.selected_client,
            key="client_pill"
        )
        if not selected_client:
            selected_client = st.session_state.selected_client
        else:
            st.session_state.selected_client = selected_client
            
    with col_talent:
        # Filter talents for the selected client
        client_talents = client_to_talents[selected_client]
        
        # Ensure currently selected talent is within the selected client's talents
        if st.session_state.selected_talent not in client_talents:
            st.session_state.selected_talent = client_talents[0]
            
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
    
    st.markdown("---")
        
    weeks_df = person_weeks(df, selected)
    talent_name = name_by_email[selected]
    
    st.title(f"👤 {talent_name}")
    st.caption(f"{len(weeks_df)} weekly check-in logs submitted")
    
    # ── Render Talent Milestones ──
    t_lower = talent_name.lower().strip()
    m_df = load_milestones_data_v2()
    matched_row = None
    if not m_df.empty and "Name" in m_df.columns:
        for _, row_m in m_df.iterrows():
            name_val = str(row_m.get("Name", "")).lower().strip()
            if not name_val or name_val == "nan":
                continue
            # Match strictly by first and last name inclusion
            if t_lower in name_val or name_val in t_lower:
                matched_row = row_m
                break

    if matched_row is not None:
        doj = str(matched_row.get("Date of joining", ""))
        months_past = str(matched_row.get("Months past", ""))
        
        if doj and doj.lower() != "nan":
            st.markdown("<br/>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Date of Joining", doj)
            m2.metric("Tenure", format_tenure(months_past))
            with m3:
                st.caption("Email Aliases")
                for e in TALENT_ROSTER[selected_talent].get("emails", [selected_talent]):
                    st.code(e, language="text")
            st.markdown("---")
            
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
                "Key Achievements": row.get("key_achievements", ""),
                "Tickets Completed": completed_val,
                "Tickets Expected": expected_val,
                "QA First Pass %": qa_val,
                "Challenges": row.get("challenges", ""),
                "Met Expectations": row.get("met_expectations", ""),
                "Overall Rating": rating_val,
                "Other Highlights": row.get("other_highlights", ""),
                "Uploads": row.get("upload", "")
            })
        else:
            # Missing submission for this week!
            progress_rows.append({
                "Week Beginning": week_begin_lbl,
                "Timestamp": "",
                "Email address": selected,
                "Key Achievements": "",
                "Tickets Completed": "",
                "Tickets Expected": "",
                "QA First Pass %": "",
                "Challenges": "",
                "Met Expectations": "",
                "Overall Rating": "",
                "Other Highlights": "",
                "Uploads": ""
            })
            
    progress_table_df = pd.DataFrame(progress_rows)
    # Build a full-width scrollable HTML table so no columns are cropped
    # Columns that should stay compact (no wrap)
    NOWRAP_COLS = {
        "Week Beginning", "Timestamp", "Email address",
        "Tickets Completed", "Tickets Expected", "QA First Pass %",
        "Overall Rating", "Met Expectations"
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

    # ── Detailed Weekly Submissions Modal ─────────────────────────────────
    if not weeks_df.empty:
        @st.dialog("Detailed Weekly Submissions", width="large")
        def show_submissions_modal(w_df):
            total_pages = len(w_df)
            if total_pages == 0:
                st.info("No submissions found.")
                return
            
            page_key = f"modal_page_{st.session_state.selected_talent}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 0
                
            def change_page(delta):
                st.session_state[page_key] += delta
                
            curr_page = st.session_state[page_key]
            
            # Fetch data for the selected week early to construct the header
            row = w_df.iloc[curr_page]
            prior = w_df.iloc[curr_page + 1] if curr_page + 1 < len(w_df) else None
            checks = week_checks(row, prior)
            week_label = format_week_label(row)
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.button("Older weeks", disabled=(curr_page == total_pages - 1), use_container_width=True, on_click=change_page, args=(1,))
            with col2:
                st.markdown(f"<div style='text-align: center; font-weight: 600; padding-top: 8px;'>Week of {week_label}</div>", unsafe_allow_html=True)
            with col3:
                st.button("Newer weeks", disabled=(curr_page == 0), use_container_width=True, on_click=change_page, args=(-1,))
            
            st.markdown("---")
            
            t_name = name_by_email.get(st.session_state.selected_talent, "Talent")
            first_name = t_name.split()[0] if t_name else "Talent"
            st.markdown(f"### What {first_name} wrote")
            
            # Text responses in a fixed 3-column grid
            col_ach, col_cha, col_hi = st.columns(3)
            with col_ach:
                st.markdown('<div class="detail-section-title">Key Achievements</div>', unsafe_allow_html=True)
                ach = str(row.get("key_achievements", "") or "").strip()
                st.markdown(f'<div class="answer-box">{ach if (ach and ach.lower() != "nan") else "*(No achievements shared)*"}</div>', unsafe_allow_html=True)
            with col_cha:
                st.markdown('<div class="detail-section-title">Challenges Faced</div>', unsafe_allow_html=True)
                cha = str(row.get("challenges", "") or "").strip()
                st.markdown(f'<div class="answer-box">{cha if (cha and cha.lower() != "nan") else "*(No challenges shared)*"}</div>', unsafe_allow_html=True)
            with col_hi:
                st.markdown('<div class="detail-section-title">Other Highlights</div>', unsafe_allow_html=True)
                hi = str(row.get("other_highlights", "") or "").strip()
                st.markdown(f'<div class="answer-box">{hi if (hi and hi.lower() != "nan") else "*(No highlights shared)*"}</div>', unsafe_allow_html=True)
                
            st.markdown("<br/>", unsafe_allow_html=True)
            
            # Numeric Stats in a fixed 4-column grid
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                met = row.get("met_expectations")
                st.metric("Met Employer Expectations", str(met) if pd.notna(met) and str(met).strip() else "N/A")
            with col2:
                completed = row.get("tickets_completed")
                expected = row.get("tickets_expected")
                tickets_val = f"{int(completed)} / {int(expected)}" if pd.notna(completed) and pd.notna(expected) else "N/A"
                st.metric("Tickets Completed", tickets_val)
            with col3:
                qa = row.get("qa_first_pass_pct")
                qa_val = f"{qa:.0f}%" if pd.notna(qa) else "N/A"
                st.metric("First-Pass QA", qa_val)
            with col4:
                rating = row.get("overall_rating")
                rating_val = f"{int(rating)} / 5" if pd.notna(rating) else "N/A"
                st.metric("Self-Rating", rating_val)

            st.markdown("---")
            for c in checks:
                _render_check(c)

        if st.button("View Detailed Weekly Submissions", type="primary", use_container_width=True):
            show_submissions_modal(weeks_df)

        st.markdown("---")
        # ── Chronological Progress Table ────────────────────────────────────────
        st.subheader("Chronological Progress History")
        st.caption("A consolidated timeline of metrics and weekly check-in entries across all weeks.")
        st.markdown(_df_to_html_table(progress_table_df), unsafe_allow_html=True)
    else:
        st.info("No detailed check-in submissions have been submitted by this talent yet.")

# --- VIEW: TEAM DIRECTORY (GDOC) ---
elif view_mode == "team_directory":
    st.title("Talent Directory")
    talent_to_client = {e: TALENT_ROSTER[e]["client"] for e in people}
    num_talents = len(people)
    num_clients = len(set(talent_to_client.values()))
    
    st.markdown("A quick look at our Talents and our Clients")
    
    overview_html = f"""
    <div style="display: flex; gap: 24px; margin-top: 16px; margin-bottom: 32px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 250px; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); border-radius: 20px; padding: 28px; box-shadow: 0 15px 35px rgba(79, 70, 229, 0.25); position: relative; overflow: hidden; color: white; transition: transform 0.2s ease-in-out;">
            <div style="position: absolute; top: -10px; right: -15px; font-size: 9rem; opacity: 0.15; line-height: 1; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.1));">👨‍💻</div>
            <div style="font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600; opacity: 0.9; margin-bottom: 12px; font-family: 'Inter', sans-serif;">Total Active Talents</div>
            <div style="font-size: 4rem; font-weight: 800; line-height: 1; font-family: 'Inter', sans-serif; text-shadow: 0px 2px 4px rgba(0,0,0,0.1);">{num_talents}</div>
        </div>
        <div style="flex: 1; min-width: 250px; background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); border-radius: 20px; padding: 28px; box-shadow: 0 15px 35px rgba(13, 148, 136, 0.25); position: relative; overflow: hidden; color: white; transition: transform 0.2s ease-in-out;">
            <div style="position: absolute; top: -10px; right: -15px; font-size: 9rem; opacity: 0.15; line-height: 1; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.1));">🏢</div>
            <div style="font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600; opacity: 0.9; margin-bottom: 12px; font-family: 'Inter', sans-serif;">Total Active Clients</div>
            <div style="font-size: 4rem; font-weight: 800; line-height: 1; font-family: 'Inter', sans-serif; text-shadow: 0px 2px 4px rgba(0,0,0,0.1);">{num_clients}</div>
        </div>
    </div>
    """
    st.markdown(overview_html, unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(
        """
        <style>
        .talent-box-link {
            box-sizing: border-box;
            transition: all 0.18s ease-in-out !important;
        }
        .talent-box-link:hover {
            border-color: #585ba6 !important;
            color: #585ba6 !important;
            background-color: #f8fafc !important;
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(88, 91, 166, 0.08) !important;
        }
        .talent-box-icon {
            color: #94a3b8;
            transition: transform 0.18s ease-in-out, color 0.18s ease-in-out !important;
        }
        .talent-box-link:hover .talent-box-icon {
            color: #585ba6 !important;
            transform: scale(1.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Group and sort talents by client
    sorted_talents = sorted(people, key=lambda e: (talent_to_client[e].lower(), name_by_email[e].lower()))
    
    import html
    html_lines = []
    
    m_df = load_milestones_data_v2()

    # Group talents by client
    client_groups = {}
    for email in sorted_talents:
        c = talent_to_client[email]
        if c not in client_groups:
            client_groups[c] = []
        client_groups[c].append(email)

    for client_name, emails in client_groups.items():
        escaped_client = html.escape(client_name)
        card_bg = "#ffffff"
        
        # Start a new grid for this client (no text header as requested)
        html_lines.append('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 24px; width: 100%; margin-bottom: 2.25rem;">')
        
        for email in emails:
            name = name_by_email[email]
            escaped_name = html.escape(name)
            escaped_email = html.escape(email)
            
            milestone_html = ""
            if not m_df.empty and "Name" in m_df.columns:
                t_lower = name.lower().strip()
                for _, row_m in m_df.iterrows():
                    name_val = str(row_m.get("Name", "")).lower().strip()
                    if name_val and name_val != "nan" and (t_lower in name_val or name_val in t_lower):
                        doj = str(row_m.get("Date of joining", ""))
                        months_past = str(row_m.get("Months past", ""))
                        if doj and doj.lower() != "nan":
                            milestone_html = (
                                f'<div style="margin-top: 12px; font-size: 0.8rem; color: #475569; padding-top: 12px; border-top: 1px dashed rgba(0,0,0,0.1); width: 100%;">'
                                f'  <strong>Joined:</strong> {html.escape(doj)}<br/>'
                                f'  <strong>Tenure:</strong> {html.escape(format_tenure(months_past))}'
                                f'</div>'
                            )
                        break
            
            all_emails = TALENT_ROSTER[email].get("emails", [email])
            escaped_emails_html = "".join([f'<div style="font-size: 0.75rem; color: #64748b; word-break: break-all; margin-bottom: 2px;">{html.escape(e)}</div>' for e in all_emails])
            
            box_html = (
                f'<a href="/?selected_talent={email}" target="_self" style="'
                f'  display: flex;'
                f'  flex-direction: column;'
                f'  align-items: center;'
                f'  justify-content: center;'
                f'  padding: 1.5rem;'
                f'  background-color: {card_bg};'
                f'  border: 1.5px solid #e2e8f0;'
                f'  border-radius: 16px;'
                f'  color: #1e293b !important;'
                f'  text-decoration: none !important;'
                f'  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);'
                f'  text-align: center;'
                f'" class="talent-box-link">'
                f'  <div class="talent-box-icon" style="font-size: 4rem; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; line-height: 1;">👤</div>'
                f'  <div style="font-weight: 700; font-size: 1.15rem; line-height: 1.25; margin-bottom: 6px; word-break: break-word;">{escaped_name}</div>'
                f'  <div style="font-weight: 600; font-size: 0.85rem; color: #585ba6; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">{escaped_client}</div>'
                f'  {escaped_emails_html}'
                f'  {milestone_html}'
                f'</a>'
            )
            html_lines.append(box_html)
            
        html_lines.append('</div>')
    st.markdown("\n".join(html_lines), unsafe_allow_html=True)


