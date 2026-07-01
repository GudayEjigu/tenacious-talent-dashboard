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
import workflow_transform
import os
import html

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHOdZugsQlciIwFckKYXqHGn8NBlXdLHJwFf3KxuabSdtXX6rlunWMx7yegMiQK6cSckTTiX6ISsH4/pub?gid=0&single=true&output=csv"
EMAIL_ALIAS_FILE = "email_aliases.csv"

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
                    else:
                        current_client = "Unassigned"
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


def ensure_unassigned_talents(source_df: pd.DataFrame | None) -> None:
    """Keep new submitters visible even when they are not in the roster yet."""
    if source_df is None or source_df.empty or "email" not in source_df.columns:
        return

    for email in source_df["email"].dropna().unique():
        email_clean = str(email).strip().lower()
        if not email_clean or email_clean in TALENT_ROSTER:
            continue
        TALENT_ROSTER[email_clean] = {
            "name": display_name(email_clean),
            "client": "Unassigned",
            "emails": [email_clean],
        }


def normalize_client_name(client: str | None) -> str:
    client_clean = str(client or "").strip()
    if client_clean.lower() == "tech":
        return "Tenacious Internal Tech Team"
    return client_clean or "Unassigned"


def find_roster_primary_by_name(name: str) -> str | None:
    target = " ".join(str(name).strip().lower().split())
    for email, info in TALENT_ROSTER.items():
        roster_name = " ".join(str(info.get("name", "")).strip().lower().split())
        if roster_name == target:
            return email
    return None


def set_roster_person(primary_email: str, name: str, client: str, aliases: list[str] | None = None) -> None:
    primary = str(primary_email).strip().lower()
    all_emails = [primary] + [str(e).strip().lower() for e in (aliases or []) if str(e).strip()]
    TALENT_ROSTER[primary] = {
        "name": name,
        "client": normalize_client_name(client),
        "emails": list(dict.fromkeys(all_emails)),
    }


def apply_roster_corrections() -> None:
    belay_primary = find_roster_primary_by_name("Belay Birhanu") or "belay@gettenacious.com"
    belay_emails = set(TALENT_ROSTER.get(belay_primary, {}).get("emails", [belay_primary]))
    belay_emails.update({"belay@gettenacious.com", "belay@10academy.org", "2belamit@gmail.com"})
    set_roster_person(belay_primary, "Belay Birhanu", "Computrition", sorted(belay_emails - {belay_primary}))

    set_roster_person(
        "estifanos@gettenacious.com",
        "Estifanos Teklay",
        "Modo",
        ["estifanosteklay1@gmail.com"],
    )
    set_roster_person(
        "meron@gettenacious.com",
        "Meron Abdo",
        "Modo",
        ["meronabdo954@gmail.com"],
    )
    set_roster_person("hiwot@gettenacious.com", "Hiwot Beyene", "Tech")
    set_roster_person("nurye@gettenacious.com", "Nurye Nigus", "Tech")
    set_roster_person(
        "yohannes@gettenacious.com",
        "Yohannes Dereje",
        "Tech",
        ["yohannesdereje1221@gmail.com"],
    )
    set_roster_person("yosef@gettenacious.com", "Yosef Zewdu", "Tech")

    GLOBAL_ALIASES.update({
        "belay@gettenacious.com": belay_primary,
        "belay@10academy.org": belay_primary,
        "2belamit@gmail.com": belay_primary,
        "estifanosteklay1@gmail.com": "estifanos@gettenacious.com",
        "meronabdo954@gmail.com": "meron@gettenacious.com",
        "yohannesdereje1221@gmail.com": "yohannes@gettenacious.com",
    })

    for alias, primary in list(GLOBAL_ALIASES.items()):
        if alias != primary and alias in TALENT_ROSTER and primary in TALENT_ROSTER:
            TALENT_ROSTER.pop(alias, None)

    for info in TALENT_ROSTER.values():
        info["client"] = normalize_client_name(info.get("client"))


apply_roster_corrections()


def _clean_email_value(email: str) -> str:
    return str(email or "").strip().lower()


def load_manual_email_aliases() -> dict[str, str]:
    """Load local alias_email -> primary_email mappings."""
    if not os.path.exists(EMAIL_ALIAS_FILE):
        return {}
    try:
        alias_df = pd.read_csv(EMAIL_ALIAS_FILE)
    except Exception:
        return {}

    aliases: dict[str, str] = {}
    col_lookup = {str(c).strip().lower(): c for c in alias_df.columns}
    alias_col = col_lookup.get("alias_email") or col_lookup.get("alias")
    primary_col = col_lookup.get("primary_email") or col_lookup.get("primary")
    if not alias_col or not primary_col:
        return {}

    for _, row in alias_df.iterrows():
        alias = _clean_email_value(row.get(alias_col))
        primary = _clean_email_value(row.get(primary_col))
        if alias and primary and alias != primary:
            aliases[alias] = primary
    return aliases


def save_manual_email_alias(alias_email: str, primary_email: str) -> None:
    alias = _clean_email_value(alias_email)
    primary = _clean_email_value(primary_email)
    if not alias or not primary or alias == primary:
        return

    existing = pd.DataFrame(columns=["alias_email", "primary_email"])
    if os.path.exists(EMAIL_ALIAS_FILE):
        try:
            existing = pd.read_csv(EMAIL_ALIAS_FILE)
        except Exception:
            existing = pd.DataFrame(columns=["alias_email", "primary_email"])

    if "alias_email" not in existing.columns or "primary_email" not in existing.columns:
        existing = pd.DataFrame(columns=["alias_email", "primary_email"])

    existing["alias_email"] = existing["alias_email"].fillna("").astype(str).str.strip().str.lower()
    existing["primary_email"] = existing["primary_email"].fillna("").astype(str).str.strip().str.lower()
    existing = existing[existing["alias_email"] != alias]
    updated = pd.concat(
        [existing, pd.DataFrame([{"alias_email": alias, "primary_email": primary}])],
        ignore_index=True,
    )
    updated.to_csv(EMAIL_ALIAS_FILE, index=False)


def combined_email_aliases() -> dict[str, str]:
    aliases = {_clean_email_value(k): _clean_email_value(v) for k, v in GLOBAL_ALIASES.items()}
    aliases.update(load_manual_email_aliases())
    return {k: v for k, v in aliases.items() if k and v and k != v}


def canonicalize_email_dataframe(source_df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Replace alternate submission emails with their primary person email."""
    if source_df is None or source_df.empty or "email" not in source_df.columns:
        return source_df

    out = source_df.copy()
    out["email"] = out["email"].astype(str).str.strip().str.lower()
    aliases = combined_email_aliases()
    if not aliases:
        return out

    def resolve(email: str) -> str:
        seen = set()
        current = _clean_email_value(email)
        while current in aliases and current not in seen:
            seen.add(current)
            current = aliases[current]
        return current

    out["email"] = out["email"].map(resolve)
    for alias, primary in aliases.items():
        if primary in TALENT_ROSTER:
            emails = TALENT_ROSTER[primary].setdefault("emails", [primary])
            if alias not in emails:
                emails.append(alias)
    return out

st.set_page_config(
    page_title="Talent Management Weekly Overview",
    page_icon="icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Styling & CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    * {
        text-decoration: none !important;
    }
    
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

    .talent-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
        width: 100%;
        margin-bottom: 2.25rem;
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
        .talent-grid {
            grid-template-columns: 1fr;
        }
        [data-testid="block-container"], .block-container {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
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

    [data-testid="block-container"], .block-container {
        max-width: 95% !important;
        margin: 0 auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    [data-testid="stHeader"] {
        display: none !important;
    }

    /* Professional top navigation theme */
    div.st-key-custom_top_navbar {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999999 !important;
        height: 78px !important;
        background: #ffffff !important;
        border-bottom: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 12px rgba(88,91,166,0.07) !important;
        padding: 0.75rem 2.5rem !important;
    }

    div.st-key-custom_top_navbar [data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }

    div.st-key-custom_top_navbar a,
    div.st-key-custom_top_navbar button {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 3px solid transparent !important;
        box-shadow: none !important;
        color: #64748b !important;
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        min-height: 0 !important;
        height: auto !important;
        padding: 0.6rem 0.5rem !important;
        transition: color 0.18s, border-color 0.18s !important;
        text-align: center !important;
    }

    div.st-key-custom_top_navbar a:hover,
    div.st-key-custom_top_navbar button:hover {
        color: #585ba6 !important;
        border-bottom-color: #e2e8f0 !important;
    }

    div.st-key-custom_top_navbar a[aria-current="page"],
    div.st-key-custom_top_navbar a[data-testid="stPageLink-NavLink"][aria-current="page"] {
        color: #585ba6 !important;
        border-bottom-color: #585ba6 !important;
        font-weight: 700 !important;
    }

    div.st-key-custom_top_navbar svg,
    div.st-key-custom_top_navbar [data-testid="stIconMaterial"] {
        display: none !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        padding-top: 92px !important;
    }

    [data-testid="stLogo"],
    [data-testid="stSidebarNav"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    [data-testid="stHeader"] nav,
    [data-testid="stTopNav"],
    [data-testid="stNav"] {
        background: #ffffff !important;
        border: none !important;
        min-height: 68px !important;
        padding: 0.45rem 2.5rem !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.55rem !important;
    }

    [data-testid="stHeader"] nav a,
    [data-testid="stTopNav"] a,
    [data-testid="stNav"] a,
    a[data-testid="stPageLink"] {
        color: #64748b !important;
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        padding: 0.85rem 0.95rem 0.75rem !important;
        border-radius: 0 !important;
        border-bottom: 3px solid transparent !important;
        background: transparent !important;
        box-shadow: none !important;
    }

    [data-testid="stHeader"] nav a:hover,
    [data-testid="stTopNav"] a:hover,
    [data-testid="stNav"] a:hover,
    a[data-testid="stPageLink"]:hover {
        color: #585ba6 !important;
        border-bottom-color: #e2e8f0 !important;
        background: transparent !important;
    }

    [data-testid="stHeader"] nav a[aria-current="page"],
    [data-testid="stTopNav"] a[aria-current="page"],
    [data-testid="stNav"] a[aria-current="page"],
    a[data-testid="stPageLink"][aria-current="page"] {
        color: #585ba6 !important;
        border-bottom-color: #585ba6 !important;
        font-weight: 700 !important;
        background: transparent !important;
    }

    [data-testid="stHeader"] svg,
    [data-testid="stTopNav"] svg,
    [data-testid="stNav"] svg,
    a[data-testid="stPageLink"] svg {
        display: none !important;
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
    .workflow-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        background: #ffffff;
        min-height: 88px;
        margin-bottom: 12px;
    }
    .workflow-card-title {
        font-size: 0.72rem !important;
        font-weight: 800;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }
    .workflow-card-value {
        font-size: 0.9rem !important;
        font-weight: 700;
        color: #1e293b;
        line-height: 1.35;
        word-break: break-word;
    }
    .workflow-card-detail {
        font-size: 0.72rem !important;
        color: #64748b;
        margin-top: 4px;
        line-height: 1.35;
    }
    .metric-chip {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        border-radius: 999px;
        padding: 7px 11px;
        margin: 4px 5px 4px 0;
        border: 1px solid #dbe3ef;
        background: #f8fafc;
        color: #64748b;
        font-weight: 700;
        font-size: 0.72rem !important;
    }
    .metric-chip.active {
        background: #eaf7f2;
        color: #0f766e;
        border-color: #7dd3c7;
    }
    .metric-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #cbd5e1;
        display: inline-block;
    }
    .metric-chip.active .metric-dot {
        background: #14b8a6;
    }
    .workflow-ledger-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
        margin: 8px 0 16px 0;
    }
    .workflow-ledger-table th {
        background: #f8fafc;
        color: #475569;
        font-weight: 800;
        padding: 10px 12px;
        border-bottom: 1px solid #e2e8f0;
        text-align: left;
    }
    .workflow-ledger-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #f1f5f9;
        vertical-align: top;
        color: #334155;
    }
    .workflow-raw-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        color: #334155;
        white-space: pre-wrap;
        line-height: 1.5;
    }
                  
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





def _workflow_card(title: str, value: str, detail: str = "") -> str:
    return (
        '<div class="workflow-card">'
        f'<div class="workflow-card-title">{html.escape(title)}</div>'
        f'<div class="workflow-card-value">{html.escape(str(value or "N/A"))}</div>'
        f'<div class="workflow-card-detail">{html.escape(str(detail or ""))}</div>'
        '</div>'
    )


def _metric_chips(metrics: list[workflow_transform.MetricState]) -> str:
    chips = []
    for metric in metrics:
        active = " active" if metric.selected else ""
        state = "selected" if metric.selected else "not selected"
        value = f" · {metric.value}" if metric.value else ""
        detail = f' title="{html.escape(metric.detail)}"' if metric.detail else ""
        chips.append(
            f'<span class="metric-chip{active}"{detail}>'
            f'<span class="metric-dot"></span>'
            f'{html.escape(metric.label)}'
            f'<span style="font-weight:600;color:#94a3b8;">{html.escape(value)}</span>'
            f'<span style="position:absolute;left:-9999px;">{state}</span>'
            '</span>'
        )
    return "".join(chips)


def _ledger_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        "<tr>"
        f"<td style='width: 32%; font-weight: 700;'>{html.escape(str(label))}</td>"
        f"<td>{html.escape(str(value or 'N/A'))}</td>"
        "</tr>"
        for label, value in rows
    )
    return (
        '<table class="workflow-ledger-table">'
        "<thead><tr><th>Metric</th><th>Held Value</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _weighted_score_table(rows: list[dict]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['group']))}</td>"
        f"<td style='font-weight:700;'>{html.escape(str(row['metric']))}</td>"
        f"<td>{int(row['points'])}</td>"
        f"<td style='color:#047857;font-weight:800;'>{int(row['earned'])}</td>"
        f"<td style='color:#b91c1c;font-weight:800;'>{int(row['missing'])}</td>"
        f"<td>{'Selected' if row['selected'] else 'Not selected'}</td>"
        f"<td>{html.escape(str(row['evidence']))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        '<table class="workflow-ledger-table">'
        "<thead><tr>"
        "<th>Group</th><th>Metric</th><th>Worth</th><th>Earned</th><th>Left</th><th>Status</th><th>Evidence / requirement</th>"
        "</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _row_week_date(row: pd.Series) -> pd.Timestamp:
    week_start, _ = workflow_transform.week_bounds(row)
    try:
        parsed = pd.to_datetime(week_start)
        if pd.notna(parsed):
            return pd.Timestamp(parsed)
    except Exception:
        pass
    ts = row.get("timestamp")
    if ts is not None and pd.notna(ts):
        return pd.Timestamp(ts)
    return pd.NaT


def _recent_client_rows(selected_email: str, selected_client: str, selected_history: pd.DataFrame | None) -> tuple[pd.DataFrame, list[pd.Timestamp]]:
    client_emails = [
        email
        for email in people
        if normalize_client_name(TALENT_ROSTER.get(email, {}).get("client", "Unassigned")) == selected_client
    ]
    client_df = df[df["email"].isin(client_emails)].copy()
    if client_df.empty:
        return pd.DataFrame(), []

    client_df["_week_date"] = client_df.apply(_row_week_date, axis=1)
    client_df = client_df.dropna(subset=["_week_date"]).sort_values("_week_date")

    anchor_df = selected_history.copy() if selected_history is not None and not selected_history.empty else client_df[client_df["email"] == selected_email].copy()
    if not anchor_df.empty:
        anchor_df["_week_date"] = anchor_df.apply(_row_week_date, axis=1)
        recent_weeks = anchor_df.dropna(subset=["_week_date"]).sort_values("_week_date")["_week_date"].drop_duplicates().tail(4).tolist()
    else:
        recent_weeks = client_df["_week_date"].drop_duplicates().tail(4).tolist()

    recent_df = client_df[client_df["_week_date"].isin(recent_weeks)].copy()
    recent_df = recent_df.drop_duplicates(subset=["email", "_week_date"], keep="last")
    recent_df["Talent"] = recent_df["email"].map(lambda email: name_by_email.get(email, display_name(email)))
    recent_df["Client"] = selected_client
    recent_df["Week"] = recent_df["_week_date"].dt.strftime("%d %b")
    recent_df["Week Date"] = recent_df["_week_date"]
    recent_df["Is Selected Talent"] = recent_df["email"].eq(selected_email)
    recent_df["Final Talent Score"] = recent_df.apply(lambda r: workflow_transform.weighted_metric_summary(r)["earned"], axis=1)
    recent_df["Points Left"] = recent_df.apply(lambda r: workflow_transform.weighted_metric_summary(r)["missing"], axis=1)
    return recent_df, recent_weeks


def _recent_metric_status(selected_recent_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    if selected_recent_df is None or selected_recent_df.empty:
        return pd.DataFrame()
    for _, recent_row in selected_recent_df.sort_values("Week Date").iterrows():
        for metric_row in workflow_transform.weighted_metric_rows(recent_row):
            records.append(
                {
                    "Week": recent_row["Week"],
                    "Week Date": recent_row["Week Date"],
                    "Group": metric_row["group"],
                    "Metric": metric_row["metric"],
                    "Metric Label": f"{metric_row['group']} · {metric_row['metric']}",
                    "Selected": bool(metric_row["selected"]),
                    "Status": "Selected" if metric_row["selected"] else "Missing",
                    "Points": int(metric_row["points"]),
                    "Earned": int(metric_row["earned"]),
                    "Evidence": metric_row["evidence"],
                    "Value": 1 if metric_row["selected"] else 0,
                }
            )
    return pd.DataFrame(records)


def _recent_all_metric_status(recent_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    if recent_df is None or recent_df.empty:
        return pd.DataFrame()
    for _, recent_row in recent_df.sort_values(["Talent", "Week Date"]).iterrows():
        for metric_row in workflow_transform.weighted_metric_rows(recent_row):
            records.append(
                {
                    "email": recent_row["email"],
                    "Talent": recent_row["Talent"],
                    "Week": recent_row["Week"],
                    "Week Date": recent_row["Week Date"],
                    "Group": metric_row["group"],
                    "Metric": metric_row["metric"],
                    "Metric Label": f"{metric_row['group']} · {metric_row['metric']}",
                    "Selected": bool(metric_row["selected"]),
                    "Points": int(metric_row["points"]),
                    "Earned": int(metric_row["earned"]),
                    "Value": 1 if metric_row["selected"] else 0,
                }
            )
    return pd.DataFrame(records)


def render_recent_client_preview(selected_email: str, talent_name: str, client: str, history_df: pd.DataFrame | None) -> None:
    st.markdown("#### Recent: last 4 weeks client view")
    st.caption(
        "A screenshot-ready management view of every talent under the same client, "
        "including score trends and scorecard metric selection across the latest four submitted weeks."
    )

    recent_df, recent_weeks = _recent_client_rows(selected_email, client, history_df)
    if recent_df.empty or not recent_weeks:
        st.info("No recent client history is available for this talent yet.")
        return

    import plotly.express as px
    import plotly.graph_objects as go

    selected_recent = recent_df[recent_df["email"] == selected_email].copy()
    recent_week_count = min(4, len(recent_weeks))
    week_order = (
        pd.DataFrame({"Week Date": recent_weeks})
        .dropna()
        .sort_values("Week Date")["Week Date"]
        .dt.strftime("%d %b")
        .tolist()
    )
    if not week_order:
        week_order = recent_df.sort_values("Week Date")["Week"].drop_duplicates().tolist()
    latest_selected_score = int(selected_recent.sort_values("Week Date")["Final Talent Score"].iloc[-1]) if not selected_recent.empty else 0
    selected_avg = selected_recent["Final Talent Score"].mean() if not selected_recent.empty else 0
    client_avg_score = recent_df["Final Talent Score"].mean() if not recent_df.empty else 0
    selected_metric_df = _recent_metric_status(selected_recent)
    selected_metric_count = int(selected_metric_df["Selected"].sum()) if not selected_metric_df.empty else 0
    client_emails = [
        email
        for email in people
        if normalize_client_name(TALENT_ROSTER.get(email, {}).get("client", "Unassigned")) == client
    ]
    client_talent_frame = pd.DataFrame(
        {
            "email": client_emails,
            "Talent": [name_by_email.get(email, display_name(email)) for email in client_emails],
        }
    ).sort_values("Talent")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(_workflow_card("Latest selected score", f"{latest_selected_score} / 100"), unsafe_allow_html=True)
    with k2:
        st.markdown(_workflow_card("4-week talent avg", f"{selected_avg:.1f} / 100"), unsafe_allow_html=True)
    with k3:
        st.markdown(_workflow_card("4-week client avg", f"{client_avg_score:.1f} / 100"), unsafe_allow_html=True)
    with k4:
        st.markdown(_workflow_card("Selected metric hits", f"{selected_metric_count}", "Across the last 4 weeks"), unsafe_allow_html=True)

    chart_left, chart_right = st.columns([1.2, 1])
    with chart_left:
        st.markdown("##### 4-week scores by client talent")
        score_fig = px.bar(
            recent_df.sort_values(["Week Date", "Talent"]),
            x="Week",
            y="Final Talent Score",
            color="Talent",
            text="Final Talent Score",
            barmode="group",
            hover_data={
                "Client": True,
                "Points Left": True,
                "Week Date": False,
                "Is Selected Talent": False,
            },
            range_y=[0, 100],
        )
        for trace in score_fig.data:
            if trace.name == talent_name:
                trace.marker.line.width = 2
                trace.marker.line.color = "#0f766e"
        score_fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
        score_fig.update_layout(
            height=380,
            margin=dict(t=20, b=30, l=8, r=8),
            xaxis_title="Last 4 weeks",
            yaxis_title="Final talent score",
            xaxis=dict(categoryorder="array", categoryarray=week_order),
            yaxis=dict(range=[0, 110]),
            legend_title="Client talent",
        )
        st.plotly_chart(score_fig, use_container_width=True)

    with chart_right:
        st.markdown("##### 4-week team average score trend")
        trend_fig = go.Figure()
        team_avg = (
            recent_df.groupby(["Week Date", "Week"], as_index=False)
            .agg(Team_Avg=("Final Talent Score", "mean"), Talents=("email", "nunique"))
            .sort_values("Week Date")
        )
        trend_fig.add_trace(
            go.Scatter(
                x=team_avg["Week"],
                y=team_avg["Team_Avg"],
                mode="lines+markers+text",
                name=f"{client} team avg",
                line=dict(color="#585ba6", width=4),
                marker=dict(size=10, color="#14b8a6"),
                text=team_avg["Team_Avg"].map(lambda v: f"{v:.0f}"),
                textposition="top center",
                customdata=team_avg[["Talents"]],
                hovertemplate=(
                    f"<b>{client} team average</b><br>"
                    "Week: %{x}<br>"
                    "Average score: %{y:.1f}/100<br>"
                    "Talents submitted: %{customdata[0]}<extra></extra>"
                ),
            )
        )
        trend_fig.update_layout(
            height=380,
            margin=dict(t=20, b=30, l=8, r=8),
            yaxis=dict(range=[0, 110], title="Average score"),
            xaxis=dict(title="Last 4 weeks", categoryorder="array", categoryarray=week_order),
            showlegend=False,
        )
        st.plotly_chart(trend_fig, use_container_width=True)

    st.markdown(f"##### {client} skill matrix: all talents")
    all_metric_df = _recent_all_metric_status(recent_df)
    if all_metric_df.empty:
        st.info("No recent scorecard metrics are available for this client window.")
    else:
        skill_summary = (
            all_metric_df.groupby(["email", "Talent", "Metric Label"], as_index=False)
            .agg(
                Selected_Weeks=("Selected", "sum"),
                Opportunities=("Selected", "count"),
                Points_Earned=("Earned", "sum"),
                Points_Possible=("Points", "sum"),
            )
        )
        skill_summary["Selection Rate Value"] = skill_summary.apply(
            lambda r: (r["Selected_Weeks"] / recent_week_count) if recent_week_count else 0,
            axis=1,
        )
        group_display_map = {
            "Signal tags": "Signal tags",
            "Growth categories": "Growth",
            "Evidence quality": "Evidence quality",
        }
        talent_order_all = client_talent_frame["Talent"].tolist()
        matrix_col, _matrix_spacer = st.columns([1, 1])
        with matrix_col:
            for group_name in ["Signal tags", "Growth categories", "Evidence quality"]:
                group_items = [item for item in workflow_transform.SCORING_WEIGHTS if item["group"] == group_name]
                metric_order = [f"{item['group']} · {item['metric']}" for item in group_items]
                metric_axis = [
                    "Ownership" if item["metric"] == "Ownership Signal" else item["metric"]
                    for item in group_items
                ]
                group_label = group_display_map.get(group_name, group_name)
                skill_matrix = skill_summary.pivot_table(
                    index="Talent",
                    columns="Metric Label",
                    values="Selection Rate Value",
                    aggfunc="max",
                    fill_value=0,
                ).reindex(index=talent_order_all, columns=metric_order, fill_value=0)
                selected_count_matrix = skill_summary.pivot_table(
                    index="Talent",
                    columns="Metric Label",
                    values="Selected_Weeks",
                    aggfunc="sum",
                    fill_value=0,
                ).reindex(index=talent_order_all, columns=metric_order, fill_value=0)
                skill_text = selected_count_matrix.astype(int).astype(str) + f"/{recent_week_count}<br>weeks"
                skill_customdata = [
                    [
                        [
                            group_label,
                            metric_axis[col_idx],
                            int(selected_count_matrix.iloc[row_idx, col_idx]),
                            recent_week_count,
                        ]
                        for col_idx in range(len(metric_axis))
                    ]
                    for row_idx in range(len(skill_matrix.index))
                ]
                st.markdown(f"**{group_label}**")
                skill_fig = go.Figure(
                    data=go.Heatmap(
                        z=skill_matrix.values,
                        x=metric_axis,
                        y=skill_matrix.index.tolist(),
                        customdata=skill_customdata,
                        colorscale=[[0, "#e2e8f0"], [0.5, "#bfdbfe"], [1, "#14b8a6"]],
                        zmin=0,
                        zmax=1,
                        showscale=False,
                        text=skill_text.values,
                        texttemplate="%{text}",
                        textfont=dict(size=8),
                        hovertemplate="<b>%{y}</b><br>%{customdata[0]} · %{customdata[1]}<br>Selected weeks: %{customdata[2]} / %{customdata[3]}<extra></extra>",
                    )
                )
                skill_fig.update_layout(
                    height=max(250, 54 * max(len(skill_matrix), 1) + 105),
                    margin=dict(t=10, b=76, l=8, r=8),
                    xaxis=dict(title=None, tickangle=-45, automargin=True),
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(skill_fig, use_container_width=True)

        submitted_summary = (
            recent_df.sort_values("Week Date")
            .groupby(["email", "Talent"], as_index=False)
            .agg(
                Recent_Submissions=("Week", "nunique"),
                Avg_Score=("Final Talent Score", "mean"),
                Latest_Score=("Final Talent Score", "last"),
                Latest_Week=("Week", "last"),
                Points_Left=("Points Left", "last"),
            )
        )
        metric_totals = (
            all_metric_df.groupby(["email", "Talent"], as_index=False)
            .agg(
                Metric_Hits=("Selected", "sum"),
                Metric_Opportunities=("Selected", "count"),
                Points_Earned=("Earned", "sum"),
                Points_Possible=("Points", "sum"),
            )
        )
        client_summary = client_talent_frame.merge(submitted_summary, on=["email", "Talent"], how="left").merge(
            metric_totals,
            on=["email", "Talent"],
            how="left",
        )
        for col in ["Recent_Submissions", "Latest_Score", "Points_Left", "Metric_Hits", "Metric_Opportunities", "Points_Earned", "Points_Possible"]:
            client_summary[col] = client_summary[col].fillna(0).astype(int)
        client_summary["Avg_Score"] = client_summary["Avg_Score"].fillna(0)
        client_summary["Latest_Week"] = client_summary["Latest_Week"].fillna("No recent submission")
        client_summary["Metric Selection Rate"] = client_summary.apply(
            lambda r: f"{(r['Metric_Hits'] / r['Metric_Opportunities']):.0%}" if r["Metric_Opportunities"] else "0%",
            axis=1,
        )
        client_summary["Avg Score"] = client_summary["Avg_Score"].map(lambda v: f"{v:.1f} / 100" if v else "No recent score")
        client_summary["Latest Score"] = client_summary["Latest_Score"].map(lambda v: f"{v} / 100" if v else "No recent score")
        client_summary["Metric Hits"] = client_summary.apply(
            lambda r: f"{r['Metric_Hits']} / {r['Metric_Opportunities']}" if r["Metric_Opportunities"] else "0 / 0",
            axis=1,
        )
        st.dataframe(
            client_summary[
                [
                    "Talent",
                    "Recent_Submissions",
                    "Latest_Week",
                    "Latest Score",
                    "Avg Score",
                    "Points_Left",
                    "Metric Hits",
                    "Metric Selection Rate",
                ]
            ].rename(
                columns={
                    "Recent_Submissions": "Recent Submissions",
                    "Latest_Week": "Latest Week",
                    "Points_Left": "Points Left",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("##### Metrics selected for the selected talent in the last 4 weeks")
    if selected_metric_df.empty:
        st.info("No scorecard metrics are available for this talent in the recent window.")
        return

    metric_order = (
        selected_metric_df.groupby("Metric Label")["Selected"]
        .sum()
        .sort_values(ascending=True)
        .index
        .tolist()
    )
    heatmap_df = selected_metric_df.pivot_table(
        index="Metric Label",
        columns="Week",
        values="Value",
        aggfunc="max",
        fill_value=0,
    ).reindex(index=metric_order)
    week_order = selected_recent.sort_values("Week Date")["Week"].drop_duplicates().tolist()
    heatmap_df = heatmap_df.reindex(columns=week_order, fill_value=0)

    heat_fig = px.imshow(
        heatmap_df,
        color_continuous_scale=[[0, "#e2e8f0"], [1, "#14b8a6"]],
        aspect="auto",
        labels=dict(x="Week", y="Scorecard metric", color="Selected"),
        zmin=0,
        zmax=1,
    )
    heat_fig.update_traces(
        text=heatmap_df.replace({1: "Selected", 0: "Missing"}).values,
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>Week: %{x}<br>Status: %{text}<extra></extra>",
    )
    heat_fig.update_layout(
        height=max(430, 26 * len(heatmap_df) + 110),
        margin=dict(t=20, b=24, l=8, r=8),
        coloraxis_showscale=False,
    )
    st.plotly_chart(heat_fig, use_container_width=True)

    metric_table = selected_metric_df.copy()
    metric_table = (
        metric_table.groupby(["Group", "Metric"], as_index=False)
        .agg(
            Selected_Weeks=("Selected", "sum"),
            Opportunities=("Selected", "count"),
            Points_Earned=("Earned", "sum"),
            Points_Possible=("Points", "sum"),
        )
        .sort_values(["Group", "Metric"])
    )
    metric_table["Selection Rate"] = metric_table.apply(
        lambda r: f"{(r['Selected_Weeks'] / r['Opportunities']):.0%}" if r["Opportunities"] else "0%",
        axis=1,
    )
    st.dataframe(
        metric_table.rename(
            columns={
                "Selected_Weeks": "Selected Weeks",
                "Opportunities": "Recent Weeks",
                "Points_Earned": "Points Earned",
                "Points_Possible": "Points Possible",
            }
        )[["Group", "Metric", "Selected Weeks", "Recent Weeks", "Selection Rate", "Points Earned", "Points Possible"]],
        use_container_width=True,
        hide_index=True,
    )


def render_transformation_snapshot(
    row: pd.Series,
    prior: pd.Series | None,
    selected_email: str,
    talent_name: str,
    history_df: pd.DataFrame | None = None,
) -> None:
    """Five-page evidence trail from Telegram input to growth report."""
    roster_info = TALENT_ROSTER.get(selected_email, {})
    client = normalize_client_name(roster_info.get("client", "Unassigned"))
    raw_email = str(row.get("email") or selected_email or "").strip().lower()
    canonical_email = selected_email
    raw_message = workflow_transform.clean_text(row.get("key_achievements"))
    timestamp_label = workflow_transform.format_submission_day(row.get("timestamp"))
    week_start, week_end = workflow_transform.week_bounds(row)
    msg_type = workflow_transform.message_type(row)
    talent_id = workflow_transform.talent_id(canonical_email, talent_name)
    client_id = workflow_transform.client_id(client)
    project_id = workflow_transform.project_id(client, row.get("week"))
    signal_metrics = workflow_transform.detect_signal_metrics(row)
    growth_metrics = workflow_transform.detect_growth_category_metrics(row)
    scorecard = workflow_transform.talent_scorecard(row)
    delta = workflow_transform.delta_from_prior(row, prior)
    story = workflow_transform.client_story(row, talent_name, client, prior)

    st.markdown(
        "<div style='margin: 0 0 10px 0; color:#64748b;'>"
        "Each page shows what the system currently holds at that transformation layer. "
        "Grey metrics are available in the framework but were not selected by this week's evidence."
        "</div>",
        unsafe_allow_html=True,
    )

    capture_tab, normalize_tab, classify_tab, score_tab, report_tab, recent_tab, history_tab = st.tabs(
        ["Capture", "Normalize", "Classify", "Score", "Report", "Recent", "History"]
    )

    with capture_tab:
        st.markdown("#### Capture: Telegram bot insertion")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(_workflow_card("Talent name", talent_name), unsafe_allow_html=True)
        with c2:
            st.markdown(_workflow_card("Email submitted", raw_email), unsafe_allow_html=True)
        with c3:
            st.markdown(
                _workflow_card("Timestamp", timestamp_label, "Day-name format for weekly review"),
                unsafe_allow_html=True,
            )
        st.markdown("**Raw message from `What were your key achievements of the week?`**")
        st.markdown(
            f'<div class="workflow-raw-box">{html.escape(raw_message or "(No achievement message captured)")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _ledger_table(
                [
                    ("Capture source", "Telegram weekly bot / form export"),
                    ("Raw evidence field", "What were your key achievements of the week?"),
                    ("Captured", "Yes" if raw_message else "No"),
                    ("Submission day", timestamp_label),
                ]
            ),
            unsafe_allow_html=True,
        )

    with normalize_tab:
        st.markdown("#### Normalize: identity, client, project, and week")
        n1, n2, n3 = st.columns(3)
        with n1:
            st.markdown(
                _workflow_card(
                    "Email identity",
                    workflow_transform.email_identity(raw_email),
                    "Domain removed from Gmail / gettenacious address",
                ),
                unsafe_allow_html=True,
            )
        with n2:
            st.markdown(
                _workflow_card(
                    "Resolved Tenacious email",
                    canonical_email,
                    "Alias and first-name matching applied before scoring",
                ),
                unsafe_allow_html=True,
            )
        with n3:
            st.markdown(_workflow_card("Client", client), unsafe_allow_html=True)
        st.markdown(
            _ledger_table(
                [
                    ("Talent ID", talent_id),
                    ("Client ID", client_id),
                    ("Project ID", project_id),
                    ("Week start", week_start),
                    ("Week end", week_end),
                    ("Message type", msg_type),
                ]
            ),
            unsafe_allow_html=True,
        )

    with classify_tab:
        st.markdown("#### Classify: signal tags and growth categories")
        st.markdown("**Signal tags**")
        st.markdown(_metric_chips(signal_metrics), unsafe_allow_html=True)
        st.markdown("**Growth categories**")
        st.markdown(_metric_chips(growth_metrics), unsafe_allow_html=True)
        active_signals = ", ".join([m.label for m in signal_metrics if m.selected]) or "None selected"
        active_categories = ", ".join([m.label for m in growth_metrics if m.selected]) or "None selected"
        st.markdown(
            _ledger_table(
                [
                    ("Selected signal tags", active_signals),
                    ("Selected growth categories", active_categories),
                    ("Classification source", "Key achievements + challenges + other highlights"),
                    ("Unselected metrics", "Still shown as grey chips for auditability"),
                ]
            ),
            unsafe_allow_html=True,
        )

    with score_tab:
        st.markdown("#### Score: rubric result and evidence quality")
        weighted_rows = workflow_transform.weighted_metric_rows(row)
        evidence_quality_metrics = [
            workflow_transform.MetricState(
                row_data["metric"],
                bool(row_data["selected"]),
                f"{row_data['earned']} / {row_data['points']} pts",
                row_data["evidence"],
            )
            for row_data in weighted_rows
            if row_data["group"] == "Evidence quality"
        ]
        score_metrics = [
            workflow_transform.MetricState("Score 1", scorecard["score_band"] == "1", "Weak / at risk"),
            workflow_transform.MetricState("Score 2", scorecard["score_band"] == "2", "Developing"),
            workflow_transform.MetricState("Score 3", scorecard["score_band"] == "3", "Strong"),
            workflow_transform.MetricState("Score 4", scorecard["score_band"] == "4", "Excellent / leading"),
        ]
        st.markdown("**Rubric selection**")
        st.markdown(_metric_chips(score_metrics), unsafe_allow_html=True)
        st.markdown("**Evidence quality metrics**")
        st.markdown(_metric_chips(evidence_quality_metrics), unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(_workflow_card("Growth score", scorecard["growth_score"]), unsafe_allow_html=True)
        with s2:
            st.markdown(_workflow_card("Confidence", scorecard["confidence"]), unsafe_allow_html=True)
        with s3:
            st.markdown(_workflow_card("Evidence strength", scorecard["evidence_strength"]), unsafe_allow_html=True)
        st.markdown(
            _ledger_table(
                [
                    ("Score", scorecard["score_band"]),
                    ("Confidence", scorecard["confidence"]),
                    ("Evidence strength", scorecard["evidence_strength"]),
                    (
                        "Evidence quality metrics",
                        "; ".join(
                            f"{m.label}: {'selected' if m.selected else 'not selected'} ({m.value})"
                            for m in evidence_quality_metrics
                        ),
                    ),
                    ("Rationale", workflow_transform.score_rationale(row)),
                    ("Reviewer", "System draft; human review recommended before client-facing use"),
                ]
            ),
            unsafe_allow_html=True,
        )

    with report_tab:
        st.markdown("#### Report: rollup into growth path")
        score_path = workflow_transform.score_to_100_breakdown(row)
        weighted_summary = workflow_transform.weighted_metric_summary(row)
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(
                _workflow_card(
                    "Final talent scorecard",
                    f"{weighted_summary['earned']} / {weighted_summary['possible']}",
                    f"{weighted_summary['missing']} points left to reach 100",
                ),
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(_workflow_card("Client scorecard", client, f"Client rollup uses {client_id}"), unsafe_allow_html=True)
        with r3:
            st.markdown(_workflow_card("Delta", delta, "Change compared with prior submitted week"), unsafe_allow_html=True)
        st.markdown("##### Scorecard metrics and evidence")
        w1, w2 = st.columns(2)
        with w1:
            st.markdown(_workflow_card("Points left", f"{weighted_summary['missing']}"), unsafe_allow_html=True)
        with w2:
            st.markdown(_workflow_card("Scoring basis", "Visible evidence", "Selected metrics earn their full assigned weight"), unsafe_allow_html=True)
        st.markdown(_weighted_score_table(weighted_summary["rows"]), unsafe_allow_html=True)
        st.markdown("##### Evidence-based score explanation")
        e1, e2 = st.columns([1, 1])
        with e1:
            earned_html = "".join(f"<li>{html.escape(item)}</li>" for item in score_path["earned"])
            st.markdown(
                "<div class='workflow-card'>"
                "<div class='workflow-card-title'>Why this score was earned</div>"
                f"<ul style='margin:0 0 0 18px; padding:0; line-height:1.55;'>{earned_html}</ul>"
                "</div>",
                unsafe_allow_html=True,
            )
        with e2:
            missing_metric_items = [
                f"{row['metric']} ({row['points']} pts): {row['evidence']}"
                for row in weighted_summary["rows"]
                if not row["selected"]
            ]
            missing_html = "".join(f"<li>{html.escape(item)}</li>" for item in missing_metric_items)
            st.markdown(
                "<div class='workflow-card'>"
                "<div class='workflow-card-title'>What is still missing to reach 100</div>"
                f"<div class='workflow-card-value'>{weighted_summary['missing']} weighted metric points still unproven</div>"
                f"<ul style='margin:8px 0 0 18px; padding:0; line-height:1.55;'>{missing_html}</ul>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("##### Requirements checklist")
        st.markdown("**Signal requirements**")
        st.markdown(_metric_chips(signal_metrics), unsafe_allow_html=True)
        st.markdown("**Growth-category requirements**")
        st.markdown(_metric_chips(growth_metrics), unsafe_allow_html=True)

        next_actions_html = "".join(f"<li>{html.escape(item)}</li>" for item in score_path["next_actions"])
        st.markdown(
            "<div class='workflow-card'>"
            "<div class='workflow-card-title'>Next actions for a stronger growth path</div>"
            f"<ul style='margin:0 0 0 18px; padding:0; line-height:1.55;'>{next_actions_html}</ul>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            _ledger_table(
                [
                    ("Final talent scorecard", f"{talent_name}: {weighted_summary['earned']} / {weighted_summary['possible']}"),
                    ("Client scorecard", f"{client}: evidence rolled up through {client_id}"),
                    ("Deltas", delta),
                    ("Scorecard point map", f"{weighted_summary['earned']} earned, {weighted_summary['missing']} left, {weighted_summary['possible']} possible"),
                    ("Why the score was earned", " ".join(score_path["earned"])),
                    ("What remains to reach 100", " ".join(missing_metric_items)),
                    ("Coaching notes", " ".join(score_path["next_actions"])),
                    ("Client-facing story", story),
                ]
            ),
            unsafe_allow_html=True,
        )

    with recent_tab:
        render_recent_client_preview(selected_email, talent_name, client, history_df)

    with history_tab:
        st.markdown("#### History: weekly final talent scorecard")
        if history_df is None or history_df.empty:
            st.info("No historical submissions are available for this talent yet.")
        else:
            import plotly.express as px

            history_rows = []
            for _, history_row in history_df.sort_values("timestamp" if "timestamp" in history_df.columns else "week").iterrows():
                hist_summary = workflow_transform.weighted_metric_summary(history_row)
                week_start_hist, week_end_hist = workflow_transform.week_bounds(history_row)
                ts = history_row.get("timestamp")
                if pd.notna(ts):
                    week_date = pd.Timestamp(ts)
                    week_label_hist = pd.Timestamp(ts).strftime("%d %b %Y")
                else:
                    try:
                        week_date = pd.to_datetime(week_start_hist)
                    except Exception:
                        week_date = pd.NaT
                    week_label_hist = week_start_hist if week_start_hist != "Unknown" else workflow_transform.clean_text(history_row.get("week"))
                history_rows.append(
                    {
                        "Week": week_label_hist,
                        "Date": week_date,
                        "Final Talent Score": hist_summary["earned"],
                        "Points Left": hist_summary["missing"],
                        "Possible": hist_summary["possible"],
                        "Week Window": f"{week_start_hist} to {week_end_hist}",
                    }
                )

            history_score_df = pd.DataFrame(history_rows)
            if "Date" in history_score_df.columns:
                history_score_df = history_score_df.sort_values("Date", na_position="last")

            latest_score = int(history_score_df["Final Talent Score"].iloc[-1]) if not history_score_df.empty else 0
            best_score = int(history_score_df["Final Talent Score"].max()) if not history_score_df.empty else 0
            avg_score = history_score_df["Final Talent Score"].mean() if not history_score_df.empty else 0

            h1, h2, h3 = st.columns(3)
            with h1:
                st.markdown(_workflow_card("Latest score", f"{latest_score} / 100"), unsafe_allow_html=True)
            with h2:
                st.markdown(_workflow_card("Best score", f"{best_score} / 100"), unsafe_allow_html=True)
            with h3:
                st.markdown(_workflow_card("Average score", f"{avg_score:.1f} / 100"), unsafe_allow_html=True)

            fig_history = px.line(
                history_score_df,
                x="Date",
                y="Final Talent Score",
                markers=True,
                hover_data={
                    "Week": True,
                    "Week Window": True,
                    "Final Talent Score": True,
                    "Points Left": True,
                    "Possible": False,
                    "Date": False,
                },
                range_y=[0, 100],
            )
            fig_history.add_hline(y=100, line_dash="dash", line_color="#14b8a6", annotation_text="100 target")
            fig_history.update_traces(line_color="#585ba6", marker=dict(size=8, color="#14b8a6"))
            fig_history.update_layout(
                height=340,
                margin=dict(t=28, b=24, l=8, r=8),
                xaxis_title="Submitted week",
                yaxis_title="Final talent score",
            )
            st.plotly_chart(fig_history, use_container_width=True)

            table_df = history_score_df.copy()
            table_df["Final Talent Score"] = table_df["Final Talent Score"].map(lambda v: f"{int(v)} / 100")
            table_df["Points Left"] = table_df["Points Left"].map(lambda v: f"{int(v)}")
            st.dataframe(
                table_df[["Week", "Week Window", "Final Talent Score", "Points Left"]],
                use_container_width=True,
                hide_index=True,
            )


@st.cache_data(ttl=300, show_spinner="Loading and enriching sheet data…")
def _load_enriched(csv_url: str | None = None):
    raw_df, parse_info = load_sheet(csv_url)
    
    # Clean future entries based on current local timestamp: May 20, 2026
    if "timestamp" in raw_df.columns:
        cutoff = pd.Timestamp("2026-05-20 23:59:59")
        raw_df["temp_ts"] = pd.to_datetime(raw_df["timestamp"]).dt.tz_localize(None)
        raw_df = raw_df[raw_df["temp_ts"] <= cutoff].drop(columns=["temp_ts"])
    
    # Map duplicate email aliases so one person stays one person across pages.
    if "email" in raw_df.columns:
        raw_df = canonicalize_email_dataframe(raw_df)
        
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

        ensure_unassigned_talents(raw_df)

    
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

def render_data_source_setup():
    import io as _io
    import os as _os
    import html as _html_esc

    # ── CSS for the upload page ──────────────────────────────────────────────
    st.markdown("""
    <style>
    .upload-hero {
        background: linear-gradient(135deg, #f8f7ff 0%, #eff6ff 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .upload-hero h2 { font-size: 1.4rem; font-weight: 800; color: #1e293b; margin-bottom: 0.3rem; }
    .upload-hero p  { color: #64748b; font-size: 0.85rem; }
    .step-badge {
        display: inline-flex; align-items: center; justify-content: center;
        width: 26px; height: 26px; border-radius: 50%;
        background: #585ba6; color: white;
        font-size: 0.75rem; font-weight: 800;
        margin-right: 8px; flex-shrink: 0;
    }
    .step-row { display: flex; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.6rem; font-size: 0.83rem; color: #334155; }
    .preview-stat { background: #f8f7ff; border: 1px solid #e2e8f0; border-radius: 10px;
                    padding: 0.75rem 1rem; text-align: center; }
    .preview-stat-num { font-size: 1.5rem; font-weight: 900; color: #585ba6; }
    .preview-stat-lbl { font-size: 0.68rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .col-found  { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;
                  padding: 2px 8px; font-size: 0.72rem; font-weight: 600; color: #166534; display: inline-block; margin: 2px; }
    .col-missing { background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
                   padding: 2px 8px; font-size: 0.72rem; font-weight: 600; color: #991b1b; display: inline-block; margin: 2px; }
    .merge-banner { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
                    padding: 0.75rem 1rem; margin: 0.75rem 0; font-size: 0.8rem; color: #92400e; }
    .replace-banner { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
                      padding: 0.75rem 1rem; margin: 0.75rem 0; font-size: 0.8rem; color: #991b1b; }
    </style>
    """, unsafe_allow_html=True)

    from data_loader import _parse_csv_text, _coerce_types, _normalize_columns, validate_sheet_dataframe, get_secret

    tab_upload, tab_link = st.tabs(["📂 Upload CSV File", "🔗 Link Google Sheet"])

    with tab_upload:

        # ── hero instructions ────────────────────────────────────────────────
        st.markdown("""
        <div class="upload-hero">
          <h2>📤 Upload Your Weekly Check-in CSV</h2>
          <p>Export from Google Sheets and drop the file below — the dashboard rebuilds automatically.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="step-row"><span class="step-badge">1</span> Open your Google Sheet with check-in responses</div>
        <div class="step-row"><span class="step-badge">2</span> Click <strong>File → Download → Comma-separated values (.csv)</strong></div>
        <div class="step-row"><span class="step-badge">3</span> Drop the file in the uploader below and choose Merge or Replace</div>
        """, unsafe_allow_html=True)

        st.markdown("")

        # ── mode selector ────────────────────────────────────────────────────
        fallback_path = "checkins_fallback.csv"
        has_existing = _os.path.exists(fallback_path)

        if has_existing:
            mode = st.radio(
                "**What should happen with existing data?**",
                options=["Merge — add new rows, keep all history", "Replace — wipe database, load only this file"],
                index=0,
                key="upload_mode_radio",
                horizontal=True,
            )
            is_replace = mode.startswith("Replace")
        else:
            is_replace = False
            st.info("No existing database found — this upload will create it.")

        # ── file uploader ────────────────────────────────────────────────────
        uploaded_file = st.file_uploader(
            "Drop your check-ins CSV here",
            type=["csv"],
            key="main_csv_uploader",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            # ── parse ────────────────────────────────────────────────────────
            try:
                raw_bytes = uploaded_file.getvalue()
                try:
                    text = raw_bytes.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw_bytes.decode("latin-1")

                raw_df, p_info = _parse_csv_text(text)
                norm_df = _coerce_types(_normalize_columns(raw_df))

            except Exception as parse_err:
                st.error(f"❌ Could not parse this file: {parse_err}")
                st.stop()

            # ── column detection ─────────────────────────────────────────────
            REQUIRED_COLS = ["email", "timestamp", "key_achievements",
                             "tickets_completed", "tickets_expected",
                             "qa_first_pass_pct", "challenges", "overall_rating"]
            OPTIONAL_COLS = ["met_expectations", "other_highlights", "upload"]

            found_req   = [c for c in REQUIRED_COLS if c in norm_df.columns]
            missing_req = [c for c in REQUIRED_COLS if c not in norm_df.columns]
            found_opt   = [c for c in OPTIONAL_COLS if c in norm_df.columns]

            # ── preview stats ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("##### 📊 File Preview")
            s1, s2, s3, s4 = st.columns(4)
            n_rows   = len(raw_df)
            n_emails = norm_df["email"].nunique() if "email" in norm_df.columns else 0
            n_weeks  = norm_df["week"].nunique()  if "week"  in norm_df.columns else 0
            n_cols   = len(norm_df.columns)

            for col, num, lbl in [
                (s1, n_rows,   "Total Rows"),
                (s2, n_emails, "Unique Emails"),
                (s3, n_weeks,  "Weeks Covered"),
                (s4, n_cols,   "Columns Parsed"),
            ]:
                col.markdown(
                    f'<div class="preview-stat"><div class="preview-stat-num">{num}</div>'
                    f'<div class="preview-stat-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True,
                )

            # ── column mapping status ────────────────────────────────────────
            st.markdown("")
            col_html = ""
            for c in found_req:
                col_html += f'<span class="col-found">✓ {_html_esc.escape(c)}</span>'
            for c in missing_req:
                col_html += f'<span class="col-missing">✗ {_html_esc.escape(c)}</span>'
            for c in found_opt:
                col_html += f'<span class="col-found">✓ {_html_esc.escape(c)} (opt)</span>'
            st.markdown(f"**Column mapping:** {col_html}", unsafe_allow_html=True)

            if p_info.repaired_rows:
                st.caption(f"ℹ️ {p_info.repaired_rows} rows auto-repaired (extra commas in text fields)")
            if p_info.skipped_rows:
                st.warning(f"⚠️ {p_info.skipped_rows} rows skipped due to unrecoverable formatting errors.")

            # ── raw data preview table ───────────────────────────────────────
            with st.expander("👁 Preview first 10 rows", expanded=False):
                preview_cols = [c for c in ["email", "timestamp", "key_achievements",
                                            "tickets_completed", "tickets_expected",
                                            "qa_first_pass_pct", "challenges"] if c in norm_df.columns]
                st.dataframe(
                    norm_df[preview_cols].head(10),
                    use_container_width=True,
                    hide_index=True,
                )

            # ── merge / replace banner ───────────────────────────────────────
            st.markdown("")
            if is_replace:
                st.markdown(
                    '<div class="replace-banner">⚠️ <strong>Replace mode:</strong> '
                    'The existing database will be wiped and replaced with only this file\'s data.</div>',
                    unsafe_allow_html=True,
                )
            elif has_existing:
                try:
                    with open(fallback_path, "r", encoding="utf-8-sig") as f:
                        exist_text = f.read()
                    exist_raw, _ = _parse_csv_text(exist_text)
                    exist_norm   = _coerce_types(_normalize_columns(exist_raw))
                    combined_tmp = pd.concat([exist_norm, norm_df], ignore_index=True)
                    if "email" in combined_tmp.columns and "timestamp" in combined_tmp.columns:
                        deduped = combined_tmp.drop_duplicates(subset=["email", "timestamp"], keep="last")
                        new_rows = len(deduped) - len(exist_norm)
                    else:
                        new_rows = n_rows
                    st.markdown(
                        f'<div class="merge-banner">🔀 <strong>Merge mode:</strong> '
                        f'Existing database has <strong>{len(exist_norm)}</strong> rows. '
                        f'This upload adds <strong>~{max(0, new_rows)}</strong> new rows '
                        f'(duplicates by email+timestamp are dropped).</div>',
                        unsafe_allow_html=True,
                    )
                except Exception:
                    st.markdown(
                        '<div class="merge-banner">🔀 <strong>Merge mode:</strong> Will merge with existing database.</div>',
                        unsafe_allow_html=True,
                    )

            # ── validate before showing confirm button ───────────────────────
            if missing_req and "email" in missing_req:
                st.error("❌ No email column found — check the file format.")
                st.stop()

            # ── confirm button ───────────────────────────────────────────────
            btn_label = "🔄 Replace Database & Rebuild Dashboard" if is_replace else "✅ Merge & Rebuild Dashboard"
            if st.button(btn_label, type="primary", use_container_width=True, key="confirm_upload_btn"):
                with st.spinner("Processing data and rebuilding dashboard…"):
                    try:
                        # --- Merge or replace ---
                        if is_replace or not has_existing:
                            final_raw_df = raw_df.copy()
                        else:
                            with open(fallback_path, "r", encoding="utf-8-sig") as f:
                                exist_text = f.read()
                            exist_raw, _ = _parse_csv_text(exist_text)
                            combined_df  = pd.concat([exist_raw, raw_df], ignore_index=True)
                            norm_combined = _coerce_types(_normalize_columns(combined_df))
                            norm_combined = norm_combined.sort_values("timestamp", na_position="first")
                            dedup_idx = norm_combined.drop_duplicates(
                                subset=["email", "timestamp"], keep="last"
                            ).index
                            final_raw_df = combined_df.loc[dedup_idx].copy()

                        # --- Save to fallback DB ---
                        final_raw_df.to_csv(fallback_path, index=False)

                        # --- Normalise & enrich ---
                        final_norm = _coerce_types(_normalize_columns(final_raw_df))
                        final_norm = canonicalize_email_dataframe(final_norm)
                        validate_sheet_dataframe(final_norm)

                        # Update TALENT_ROSTER with any new emails discovered in this CSV
                        if "email" in final_norm.columns:
                            for em in final_norm["email"].dropna().unique():
                                em_clean = str(em).strip().lower()
                                if em_clean and em_clean not in TALENT_ROSTER:
                                    TALENT_ROSTER[em_clean] = {
                                        "name": display_name(em_clean),
                                        "client": "Unassigned",
                                        "emails": [em_clean],
                                    }

                        import growth_signal_engine as _gse, scoring as _sc
                        df_engine = _gse.process_dataframe(final_norm)
                        df_engine["spec_growth_tier"] = df_engine["growth_tier"]
                        df_scored = _sc.enrich_dataframe(df_engine.drop(columns=["growth_tier"]))
                        df_scored["growth_tier"] = df_scored["spec_growth_tier"]

                        st.session_state.uploaded_df           = df_scored
                        st.session_state.uploaded_parse_info   = p_info
                        st.cache_data.clear()

                        n_final = len(df_scored)
                        n_talent = df_scored["email"].nunique() if "email" in df_scored.columns else "?"
                        st.success(
                            f"✅ Dashboard rebuilt! {n_final} total rows · {n_talent} talents · "
                            f"{df_scored['week'].nunique() if 'week' in df_scored.columns else '?'} weeks"
                        )
                        st.rerun()

                    except Exception as ex:
                        st.error(f"❌ Failed to rebuild: {ex}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")

    with tab_link:
        st.markdown("#### Paste your Google Sheet sharing link:")
        st.info(
            "**Important:** Make sure the sheet's general access is set to **'Anyone with the link can view'** "
            "so the dashboard can fetch the data automatically."
        )
        saved_url = get_secret("sheet_csv_url", "")
        override = st.text_input(
            "Google Sheets Link (shared or published CSV URL)",
            value=saved_url,
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="gsheet_url_input",
        )
        if st.button("🔗 Connect to Google Sheet", type="primary", key="gsheet_connect_btn"):
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
            else:
                st.warning("Please paste a Google Sheets link first.")


# 3. If no data has been loaded, display the beautiful branded setup/upload screen!
if df is None:
    render_data_source_setup()
    st.stop()

if parse_info and (parse_info.repaired_rows or parse_info.skipped_rows):
    st.warning(
        f"Parsed with repairs: {parse_info.repaired_rows} fixed, {parse_info.skipped_rows} skipped."
    )

if "email" not in df.columns:
    st.error("No email column in sheet.")
    st.stop()

df = canonicalize_email_dataframe(df)
ensure_unassigned_talents(df)
df["talent"] = df["email"].map(display_name)
# All known talents from the roster plus anyone who submitted data.
_submitted_emails = {str(e).strip().lower() for e in df["email"].dropna().unique()}
_all_people = set(TALENT_ROSTER.keys()) | _submitted_emails
people = sorted(_all_people, key=lambda e: display_name(e))
name_by_email = {e: display_name(e) for e in people}

# Filter valid unique weeks globally so they are available in both views
unique_weeks = sorted(df["week"].dropna().unique().tolist())
unique_weeks = [w for w in unique_weeks if w and str(w) != "NaT"]

if "selected_talent" not in st.session_state:
    st.session_state.selected_talent = people[0] if people else None


def page_data_source():
    st.markdown("<br>", unsafe_allow_html=True)
    render_data_source_setup()


def render_evidence_review_body(selected: str, key_prefix: str = "evidence") -> None:
    weeks_df = person_weeks(df, selected)
    if weeks_df.empty:
        st.info("No detailed check-in submissions have been submitted by this talent yet.")
        return

    page_key = f"{key_prefix}_page_{selected}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    st.session_state[page_key] = max(0, min(st.session_state[page_key], len(weeks_df) - 1))

    def change_page(delta: int) -> None:
        st.session_state[page_key] = max(0, min(st.session_state[page_key] + delta, len(weeks_df) - 1))

    curr_page = st.session_state[page_key]
    row = weeks_df.iloc[curr_page]
    prior = weeks_df.iloc[curr_page + 1] if curr_page + 1 < len(weeks_df) else None
    checks = week_checks(row, prior)
    week_label = format_week_label(row)
    talent_name = name_by_email.get(selected, "Talent")
    first_name = talent_name.split()[0] if talent_name else "Talent"
    client = normalize_client_name(TALENT_ROSTER.get(selected, {}).get("client", "Unassigned"))

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.button(
            "Older weeks",
            disabled=(curr_page == len(weeks_df) - 1),
            use_container_width=True,
            on_click=change_page,
            args=(1,),
            key=f"{key_prefix}_older_week",
        )
    with col2:
        st.markdown(
            f"<div style='text-align: center; font-weight: 700; padding-top: 8px;'>"
            f"{talent_name} · {client}<br><span style='font-weight: 500; color: #64748b;'>Week of {week_label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.button(
            "Newer weeks",
            disabled=(curr_page == 0),
            use_container_width=True,
            on_click=change_page,
            args=(-1,),
            key=f"{key_prefix}_newer_week",
        )

    st.markdown("---")
    render_transformation_snapshot(row, prior, selected, talent_name, weeks_df)

    st.markdown("---")
    st.markdown(f"### What {first_name} wrote")

    col_ach, col_cha, col_hi = st.columns(3)
    with col_ach:
        st.markdown('<div class="detail-section-title">Key Achievements</div>', unsafe_allow_html=True)
        ach = str(row.get("key_achievements", "") or "").strip()
        st.markdown(
            f'<div class="answer-box">{ach if (ach and ach.lower() != "nan") else "*(No achievements shared)*"}</div>',
            unsafe_allow_html=True,
        )
    with col_cha:
        st.markdown('<div class="detail-section-title">Challenges Faced</div>', unsafe_allow_html=True)
        cha = str(row.get("challenges", "") or "").strip()
        st.markdown(
            f'<div class="answer-box">{cha if (cha and cha.lower() != "nan") else "*(No challenges shared)*"}</div>',
            unsafe_allow_html=True,
        )
    with col_hi:
        st.markdown('<div class="detail-section-title">Other Highlights</div>', unsafe_allow_html=True)
        hi = str(row.get("other_highlights", "") or "").strip()
        st.markdown(
            f'<div class="answer-box">{hi if (hi and hi.lower() != "nan") else "*(No highlights shared)*"}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

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


def page_evidence_review():
    st.title("Evidence Review")
    st.caption("Review each weekly submission, transformation snapshot, raw writing, and score rationale.")

    talent_to_client = {e: TALENT_ROSTER.get(e, {}).get("client") or "Unassigned" for e in people}
    client_to_talents = {}
    for e in people:
        client_to_talents.setdefault(talent_to_client[e], []).append(e)

    clients = sorted(client_to_talents.keys())
    curr_talent = st.session_state.selected_talent if st.session_state.selected_talent in people else people[0]
    curr_client = talent_to_client[curr_talent]
    if "evidence_selected_client" not in st.session_state or st.session_state.evidence_selected_client not in clients:
        st.session_state.evidence_selected_client = curr_client

    col_client, col_talent = st.columns(2)
    with col_client:
        selected_client = st.pills(
            "Filter by Client / Project",
            clients,
            selection_mode="single",
            default=st.session_state.evidence_selected_client,
            key="evidence_client_pill",
        )
        selected_client = selected_client or st.session_state.evidence_selected_client
        st.session_state.evidence_selected_client = selected_client

    with col_talent:
        client_talents = client_to_talents[selected_client]
        if st.session_state.selected_talent not in client_talents:
            st.session_state.selected_talent = client_talents[0]
        selected_talent = st.pills(
            "Select Talent",
            client_talents,
            selection_mode="single",
            default=st.session_state.selected_talent,
            format_func=lambda e: name_by_email[e],
            key="evidence_talent_pill",
        )
        selected_talent = selected_talent or st.session_state.selected_talent
        st.session_state.selected_talent = selected_talent

    st.markdown("---")
    render_evidence_review_body(st.session_state.selected_talent)


def page_weekly_status():
        
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
    st.title("Talent Management Weekly Overview")
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
                        link_html = f'<a href="{html.escape(val_str)}" target="_blank" style="color: #3b82f6; font-weight: 600; text-decoration: none; display: block; padding: 12px 16px;">Open Link</a>'
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

def page_talent_profiles():
    st.title("Select Talent Profile")
    
    # Build client-talent mappings dynamically
    talent_to_client = {e: TALENT_ROSTER.get(e, {}).get("client") or "Unassigned" for e in people}
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
    
    # --- PHASE 1: DATA PREPARATION (UPFRONT) ---
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
        start_part = week_str.split("/")[0].strip()
        try:
            week_dt = pd.to_datetime(start_part)
        except Exception:
            week_dt = None

        tickets_done = _safe_float(r.get("tickets_completed"))
        tickets_expected = _safe_float(r.get("tickets_expected"))
        qa_val = _safe_float(r.get("qa_first_pass_pct"))
        growth_val = _safe_float(r.get("growth_score"))

        # self rating
        s_val = r.get("overall_rating")
        if pd.isna(s_val) or str(s_val).strip() == "":
            self_val = None
        else:
            s = str(s_val).strip().lower()
            if s == "excellent": self_val = 100.0
            elif s == "above average": self_val = 80.0
            elif s == "average": self_val = 60.0
            elif s == "below average": self_val = 40.0
            elif s == "poor": self_val = 20.0
            else:
                try: self_val = float(s_val) * 20
                except: self_val = None

        # ticket comp %
        if tickets_done is not None and tickets_expected is not None and tickets_expected > 0:
            tick_pct = min(100.0, (tickets_done / tickets_expected) * 100.0)
        else:
            tick_pct = None

        # composite
        parts = [v for v in [tick_pct, qa_val, growth_val, self_val] if v is not None]
        comp_val = sum(parts) / len(parts) if parts else None

        trend_rows.append({
            "Date": week_dt,
            "Tickets Done": tickets_done,
            "Tickets Expected": tickets_expected,
            "Ticket Completion %": tick_pct,
            "QA Pass Rate": qa_val,
            "Growth Score": growth_val,
            "Self Rating": self_val,
            "Composite Score": comp_val
        })
    trend_columns = [
        "Date",
        "Tickets Done",
        "Tickets Expected",
        "Ticket Completion %",
        "QA Pass Rate",
        "Growth Score",
        "Self Rating",
        "Composite Score",
    ]
    trend_df = pd.DataFrame(trend_rows, columns=trend_columns)
    if "Date" in trend_df.columns:
        trend_df = (
            trend_df
            .dropna(subset=["Date"])
            .sort_values("Date", ascending=True)
            .set_index("Date")
        )


    # Define helper variables for visuals
    latest_data = trend_df.iloc[-1] if not trend_df.empty else None
    latest = latest_data
    prev = trend_df.iloc[-2] if len(trend_df) >= 2 else None

    # --- PHASE 2: VISUAL RENDERING (TABS FIRST) ---
    # Load Milestones & Metadata Upfront
    t_lower = talent_name.lower().strip()
    m_df = load_milestones_data_v2()
    matched_row = None
    if not m_df.empty and "Name" in m_df.columns:
        for _, row_m in m_df.iterrows():
            name_val = str(row_m.get("Name", "")).lower().strip()
            if not name_val or name_val == "nan":
                continue
            if t_lower in name_val or name_val in t_lower:
                matched_row = row_m
                break

    doj = None
    tenure_lbl = None
    if matched_row is not None:
        doj_val = str(matched_row.get("Date of joining", ""))
        if doj_val and doj_val.lower() != "nan":
            doj = doj_val
            months_past = str(matched_row.get("Months past", ""))
            tenure_lbl = format_tenure(months_past)

    emails = TALENT_ROSTER[selected_talent].get("emails", [selected_talent])

    # Compact header columns to display metadata inline next to the talent name
    if doj and tenure_lbl:
        col_name, col_doj, col_tenure, col_emails = st.columns([3.0, 1.2, 1.2, 2.6])
        with col_name:
            st.title(f"👤 {talent_name}")
            st.caption(f"{len(weeks_df)} weekly check-in logs submitted")
        with col_doj:
            st.markdown(
                f"<div style='margin-top: 16px;'>"
                f"<div style='font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;'>Join Date</div>"
                f"<div style='font-size: 13px; font-weight: 500; color: #1e293b; margin-top: 4px;'>{doj}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_tenure:
            st.markdown(
                f"<div style='margin-top: 16px;'>"
                f"<div style='font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;'>Tenure</div>"
                f"<div style='font-size: 13px; font-weight: 500; color: #1e293b; margin-top: 4px;'>{tenure_lbl}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_emails:
            emails_html = "".join([f"<code style='font-size: 11px; padding: 2px 6px; background: #f1f5f9; color: #475569; border-radius: 4px; display: inline-block; margin: 2px 4px 2px 0; border: 1px solid #e2e8f0;'>{e}</code>" for e in emails])
            st.markdown(
                f"<div style='margin-top: 16px;'>"
                f"<div style='font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;'>Email Aliases</div>"
                f"<div style='margin-top: 4px; line-height: 1.2;'>{emails_html}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        col_name, col_emails = st.columns([4.0, 4.0])
        with col_name:
            st.title(f"👤 {talent_name}")
            st.caption(f"{len(weeks_df)} weekly check-in logs submitted")
        with col_emails:
            emails_html = "".join([f"<code style='font-size: 11px; padding: 2px 6px; background: #f1f5f9; color: #475569; border-radius: 4px; display: inline-block; margin: 2px 4px 2px 0; border: 1px solid #e2e8f0;'>{e}</code>" for e in emails])
            st.markdown(
                f"<div style='margin-top: 16px;'>"
                f"<div style='font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;'>Email Aliases</div>"
                f"<div style='margin-top: 4px; line-height: 1.2;'>{emails_html}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    
    if not weeks_df.empty:
        # Render tabs first directly under name
        if len(trend_df) >= 1:
            import plotly.graph_objects as go
            import plotly.express as px

            latest_data = trend_df.iloc[-1]

            tabs = st.tabs(["Composite Score", "Ticket Completion %", "QA Pass Rate", "Growth Score", "Self Rating"])

            with tabs[0]:
                col_snap, col_trend = st.columns([1, 2])
                with col_snap:
                    cats = ["Ticket %", "QA %", "Growth", "Self Rating"]
                    vals = [
                        latest_data.get("Ticket Completion %"),
                        latest_data.get("QA Pass Rate"),
                        latest_data.get("Growth Score"),
                        latest_data.get("Self Rating")
                    ]
                    vals = [v if pd.notna(v) else 0 for v in vals]
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=cats + [cats[0]],
                        fill='toself',
                        line_color='#585ba6'
                    ))
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=250
                    )
                    st.markdown("**Latest Breakdown**")
                    st.plotly_chart(fig_radar, use_container_width=True)

                with col_trend:
                    st.markdown("**Historical Trend**")
                    comp_series = trend_df[["Composite Score"]].dropna()
                    if not comp_series.empty:
                        fig_line = px.line(comp_series.reset_index(), x="Date", y="Composite Score", markers=True, color_discrete_sequence=["#585ba6"])
                        fig_line.update_layout(yaxis_range=[0, 100], margin=dict(t=20, b=20, l=0, r=0), height=250)
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.caption("No historical data.")

            with tabs[1]:
                col_snap, col_trend = st.columns([1, 2])
                with col_snap:
                    tc_val = latest_data.get("Ticket Completion %")
                    tc_val = tc_val if pd.notna(tc_val) else 0
                    fig_bullet = go.Figure(go.Indicator(
                        mode="number+gauge",
                        value=tc_val,
                        domain={'x': [0.1, 1], 'y': [0.2, 0.9]},
                        title={'text': "Completion %", 'font': {'size': 12}},
                        gauge={
                            'shape': "bullet",
                            'axis': {'range': [None, 120]},
                            'threshold': {'line': {'color': "green", 'width': 2}, 'thickness': 0.75, 'value': 100},
                            'steps': [
                                {'range': [0, 80], 'color': "lightgray"},
                                {'range': [80, 100], 'color': "gray"}
                            ],
                            'bar': {'color': "#585ba6"}
                        }
                    ))
                    fig_bullet.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
                    st.markdown("**Latest Target %**")
                    st.plotly_chart(fig_bullet, use_container_width=True)
                with col_trend:
                    st.markdown("**Historical Expected vs Done**")
                    tick_df = trend_df[["Tickets Done", "Tickets Expected"]].copy()
                    tick_df["Tickets Done"] = pd.to_numeric(tick_df["Tickets Done"], errors="coerce")
                    tick_df["Tickets Expected"] = pd.to_numeric(tick_df["Tickets Expected"], errors="coerce")
                    tick_df = tick_df.dropna(how="all").reset_index()
                    if not tick_df.empty:
                        fig_bar = px.bar(tick_df, x="Date", y=["Tickets Done", "Tickets Expected"], barmode='group', color_discrete_sequence=["#585ba6", "#c4b5fd"])
                        fig_bar.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=250, xaxis_title="", yaxis_title="Tickets", legend_title="")
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.caption("No historical data.")

            with tabs[2]:
                col_snap, col_trend = st.columns([1, 2])
                with col_snap:
                    qa_val = latest_data.get("QA Pass Rate")
                    qa_val = qa_val if pd.notna(qa_val) else 0
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=qa_val,
                        title={'text': "QA %"},
                        gauge={'axis': {'range': [None, 100]},
                               'bar': {'color': "#4f46e5"},
                               'steps': [{'range': [0, 80], 'color': "#fca5a5"}, {'range': [80, 95], 'color': "#fef08a"}],
                               'threshold': {'line': {'color': "green", 'width': 4}, 'thickness': 0.75, 'value': 95}}
                    ))
                    fig_gauge.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
                    st.markdown("**Latest QA Pass Rate**")
                    st.plotly_chart(fig_gauge, use_container_width=True)
                with col_trend:
                    st.markdown("**Historical QA Pass Rate**")
                    qa_series = trend_df[["QA Pass Rate"]].dropna().reset_index()
                    if not qa_series.empty:
                        fig_line_qa = px.line(qa_series, x="Date", y="QA Pass Rate", markers=True, color_discrete_sequence=["#4f46e5"])
                        fig_line_qa.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Target 95%")
                        fig_line_qa.update_layout(yaxis_range=[50, 105], margin=dict(t=20, b=20, l=0, r=0), height=250, xaxis_title="", yaxis_title="QA %")
                        st.plotly_chart(fig_line_qa, use_container_width=True)
                    else:
                        st.caption("No historical QA data.")

            with tabs[3]:
                col_snap, col_trend = st.columns([1, 2])
                with col_snap:
                    gs_val = latest_data.get("Growth Score")
                    gs_val = gs_val if pd.notna(gs_val) else 0
                    fig_gs = go.Figure(go.Indicator(
                        mode="number+delta",
                        value=gs_val,
                        delta={'reference': trend_df.iloc[-2].get("Growth Score") if len(trend_df) >= 2 and pd.notna(trend_df.iloc[-2].get("Growth Score")) else 0, 'relative': False},
                        title={'text': "Growth Score"}
                    ))
                    fig_gs.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
                    st.markdown("**Latest Growth Score**")
                    st.plotly_chart(fig_gs, use_container_width=True)
                with col_trend:
                    st.markdown("**Historical Growth Trajectory**")
                    gs_series = trend_df[["Growth Score"]].dropna().reset_index()
                    if not gs_series.empty:
                        fig_step = px.line(gs_series, x="Date", y="Growth Score", line_shape="vh", markers=True, color_discrete_sequence=["#059669"])
                        fig_step.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=250, xaxis_title="", yaxis_title="Growth Score")
                        st.plotly_chart(fig_step, use_container_width=True)
                    else:
                        st.caption("No historical Growth data.")

            with tabs[4]:
                col_snap, col_trend = st.columns([1, 2])
                with col_snap:
                    sr_val = latest_data.get("Self Rating")
                    sr_val = sr_val if pd.notna(sr_val) else 0
                    fig_sr = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=sr_val,
                        title={'text': "Self Rating"},
                        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "#db2777"}}
                    ))
                    fig_sr.update_layout(height=250, margin=dict(t=20, b=20, l=20, r=20))
                    st.markdown("**Latest Self Rating**")
                    st.plotly_chart(fig_sr, use_container_width=True)

                with col_trend:
                    st.markdown("**Self Rating vs Objective Composite**")
                    dual_df = trend_df[["Self Rating", "Composite Score"]].dropna(how="all").reset_index()
                    if not dual_df.empty:
                        fig_dual = px.line(dual_df, x="Date", y=["Self Rating", "Composite Score"], markers=True, color_discrete_sequence=["#db2777", "#585ba6"])
                        fig_dual.update_layout(yaxis_range=[0, 105], margin=dict(t=20, b=20, l=0, r=0), height=250, xaxis_title="", yaxis_title="Score", legend_title="")
                        st.plotly_chart(fig_dual, use_container_width=True)
                    else:
                        st.caption("No historical Self Rating data.")

            metric_counts = workflow_transform.metric_selection_counts(weeks_df)
            if not metric_counts.empty:
                st.markdown("### Scorecard Metric Counter")
                st.caption(
                    "Counts how many submitted weeks selected each scorecard metric for this talent. "
                    "Missing counts show the remaining evidence gaps across their history."
                )
                counter_chart_df = metric_counts.melt(
                    id_vars=["group", "metric", "points", "selection_rate"],
                    value_vars=["times_selected", "times_missing"],
                    var_name="status",
                    value_name="weeks",
                )
                counter_chart_df["Status"] = counter_chart_df["status"].map(
                    {
                        "times_selected": "Selected",
                        "times_missing": "Not selected",
                    }
                )
                counter_chart_df["Metric"] = counter_chart_df["group"] + " · " + counter_chart_df["metric"]
                counter_chart_df["Group"] = counter_chart_df["group"]
                metric_order = (
                    metric_counts.assign(Metric=lambda d: d["group"] + " · " + d["metric"])["Metric"]
                    .tolist()
                )
                counter_fig = px.bar(
                    counter_chart_df,
                    x="weeks",
                    y="Metric",
                    color="Status",
                    orientation="h",
                    barmode="stack",
                    color_discrete_map={"Selected": "#14b8a6", "Not selected": "#e2e8f0"},
                    custom_data=["points", "selection_rate", "Group"],
                    category_orders={"Metric": metric_order[::-1], "Status": ["Selected", "Not selected"]},
                    height=max(560, 32 * len(metric_counts) + 120),
                )
                counter_fig.update_traces(
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Group: %{customdata[2]}<br>"
                        "Metric worth: %{customdata[0]} pts/week<br>"
                        "Weeks: %{x}<br>"
                        "Selection rate: %{customdata[1]:.0%}<extra></extra>"
                    )
                )
                counter_fig.update_layout(
                    margin=dict(t=24, b=24, l=8, r=8),
                    xaxis_title="Submitted weeks",
                    yaxis_title="",
                    legend_title="Metric state",
                    bargap=0.18,
                )
                st.plotly_chart(counter_fig, use_container_width=True)

                counter_table = metric_counts.copy()
                counter_table["Selection Rate"] = counter_table["selection_rate"].map(lambda v: f"{v:.0%}")
                counter_table = counter_table.rename(
                    columns={
                        "group": "Group",
                        "metric": "Metric",
                        "points": "Worth / Week",
                        "times_selected": "Selected Weeks",
                        "times_missing": "Missing Weeks",
                        "opportunities": "Total Weeks",
                        "points_earned": "Points Earned",
                        "points_possible": "Points Possible",
                    }
                )
                st.dataframe(
                    counter_table[
                        [
                            "Group",
                            "Metric",
                            "Worth / Week",
                            "Selected Weeks",
                            "Missing Weeks",
                            "Total Weeks",
                            "Selection Rate",
                            "Points Earned",
                            "Points Possible",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        
        st.markdown("---")
        
        # Render Sparkline Trend

        
        # Render Milestones
        # (Milestones are now rendered compactly in the header alongside the talent name)


        

        
        # Render Dialog button and table
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
                modal_client = normalize_client_name(TALENT_ROSTER.get(st.session_state.selected_talent, {}).get("client", "Unassigned"))
                st.markdown(f"### {t_name} · {modal_client}")
                render_transformation_snapshot(row, prior, st.session_state.selected_talent, t_name, w_df)

                st.markdown("---")
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

            # Detailed Submissions Button is now rendered next to the Chronological Progress History title below
            pass

        st.markdown("---")
        # ── Chronological Progress Table & Detailed Weekly Submissions Button ──
        col_title, col_btn = st.columns([3.2, 1.8])
        with col_title:
            st.subheader("Chronological Progress History")
            st.caption("A consolidated timeline of metrics and weekly check-in entries across all weeks.")
        with col_btn:
            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            if st.button("View Detailed Weekly Submissions", type="primary", use_container_width=True):
                st.session_state[f"evidence_page_{st.session_state.selected_talent}"] = 0
                st.switch_page(evidence_review_page)

        st.markdown(_df_to_html_table(progress_table_df), unsafe_allow_html=True)

    else:
        st.info("No detailed check-in submissions have been submitted by this talent yet.")
        
def page_team_overview():
    # Header row with title on left and compact controls on the right
    col_header, col_ctrls = st.columns([3.5, 2.0])
    with col_header:
        st.title("Team Overview")
        st.caption("Track the week-by-week progress trajectories of all talents across all weeks")
        
    with col_ctrls:
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("<div style='font-size: 11px; font-weight: 600; color: #64748b; margin-bottom: 2px;'>SORT BY</div>", unsafe_allow_html=True)
                hm_sort_by = st.selectbox(
                    "Sort Rows By",
                    ["Average Score (Worst First)", "Average Score (Best First)", "Client Group", "Alphabetical"],
                    key="heatmap_sort",
                    label_visibility="collapsed"
                )
            with c2:
                st.markdown("<div style='font-size: 11px; font-weight: 600; color: #64748b; margin-bottom: 8px;'>DISPLAY</div>", unsafe_allow_html=True)
                hm_show_values = st.checkbox("Show Values", value=True, key="heatmap_show_vals")
                
    # Split layout into left column (filters side panel) and right column (graphs)
    col_filters, col_graphs = st.columns([1.2, 4.8])
    
    with col_filters:
        with st.container(border=True):
            f_col1, f_col2 = st.columns([1.8, 1.0])
            f_col1.markdown("<h4 style='margin:0; font-size:15px; font-family:Montserrat, sans-serif; font-weight:600;'>🎯 Filters</h4>", unsafe_allow_html=True)
            if f_col2.button("Reset", key="reset_filters_btn", use_container_width=True):
                st.session_state.overview_selected_clients = []
                st.session_state.overview_selected_emails = []
                if "overview_client_pills" in st.session_state:
                    st.session_state.overview_client_pills = []
                if "overview_talent_pills" in st.session_state:
                    st.session_state.overview_talent_pills = []
                st.rerun()
            
            st.markdown("---")
            
            unique_clients = sorted(list({TALENT_ROSTER.get(e, {}).get("client") or "Unassigned" for e in people}))
            
            if "overview_selected_clients" not in st.session_state:
                st.session_state.overview_selected_clients = []
                
            selected_clients = st.pills(
                "Filter by Client",
                unique_clients,
                selection_mode="multi",
                default=st.session_state.overview_selected_clients,
                key="overview_client_pills"
            )
            st.session_state.overview_selected_clients = selected_clients
            
            active_clients = selected_clients if selected_clients else unique_clients
            
            filtered_people = [
                e for e in people 
                if (TALENT_ROSTER.get(e, {}).get("client") or "Unassigned") in active_clients
            ]
            all_talents = sorted(filtered_people)
            
            if "overview_selected_emails" not in st.session_state:
                st.session_state.overview_selected_emails = []
                
            current_defaults = [e for e in st.session_state.overview_selected_emails if e in all_talents]
                
            selected_emails = st.pills(
                "Filter Talents",
                all_talents,
                selection_mode="multi",
                default=current_defaults,
                format_func=lambda e: name_by_email.get(e, display_name(e)),
                key="overview_talent_pills"
            )
            st.session_state.overview_selected_emails = selected_emails
            
            active_emails = selected_emails if selected_emails else all_talents
            
    with col_graphs:
        if not active_emails:
            st.warning("Please select at least one talent to display.")
        else:
            overview_df = df[df["email"].isin(active_emails)].copy()
            
            import plotly.graph_objects as go
            import numpy as np
            
            ALL_METRICS = [
                "Composite Score",
                "Ticket Completion %",
                "QA Pass Rate",
                "Growth Score",
                "Self Rating",
            ]
            
            def _safe_float_hm(v, is_rating=False):
                if pd.isna(v) or str(v).strip() == "": return None
                if is_rating:
                    s = str(v).strip().lower()
                    if s == "excellent": return 5.0
                    elif s == "above average": return 4.0
                    elif s == "average": return 3.0
                    elif s == "below average": return 2.0
                    elif s == "poor": return 1.0
                try: return float(v)
                except ValueError: return None
            
            def _compute_metric_value(row, metric_name):
                if metric_name == "Ticket Completion %":
                    comp = _safe_float_hm(row.get("tickets_completed"))
                    exp = _safe_float_hm(row.get("tickets_expected"))
                    return round((comp / exp) * 100, 0) if comp is not None and exp is not None and exp > 0 else None
                elif metric_name == "QA Pass Rate":
                    qa = _safe_float_hm(row.get("qa_first_pass_pct"))
                    return round(qa, 0) if qa is not None else None
                elif metric_name == "Growth Score":
                    gs = _safe_float_hm(row.get("growth_score"))
                    return round(gs, 0) if gs is not None else None
                elif metric_name == "Self Rating":
                    rat = _safe_float_hm(row.get("overall_rating"), is_rating=True)
                    return round(rat * 20, 0) if rat is not None else None
                else:  # Composite Score
                    parts = []
                    comp = _safe_float_hm(row.get("tickets_completed"))
                    exp = _safe_float_hm(row.get("tickets_expected"))
                    if comp is not None and exp is not None and exp > 0:
                        parts.append(min(100, (comp / exp) * 100))
                    qa = _safe_float_hm(row.get("qa_first_pass_pct"))
                    if qa is not None:
                        parts.append(qa)
                    gs = _safe_float_hm(row.get("growth_score"))
                    if gs is not None:
                        parts.append(gs)
                    rat = _safe_float_hm(row.get("overall_rating"), is_rating=True)
                    if rat is not None:
                        parts.append(rat * 20)
                    return round(sum(parts) / len(parts), 0) if parts else None
            
            def _parse_week_sort_key_hm(w):
                try:
                    parts = w.split("-")
                    return f"{parts[0]}-{parts[1]}-{parts[2].split('/')[0]}"
                except Exception:
                    return w
            
            # ── Render each metric as its own heatmap ──
            heatmap_tabs = st.tabs(ALL_METRICS)
            for metric_idx, heatmap_metric in enumerate(ALL_METRICS):
                with heatmap_tabs[metric_idx]:
                    hm_rows = []
                    for _, row in overview_df.iterrows():
                        email = row.get("email")
                        week_str = str(row.get("week", ""))
                        if pd.isna(week_str) or not week_str.strip():
                            continue
                        talent_name = name_by_email.get(email, display_name(email))
                        client = TALENT_ROSTER.get(email, {}).get("client") or "Unassigned"
                        val = _compute_metric_value(row, heatmap_metric)
                        hm_rows.append({
                            "talent_name": talent_name,
                            "email": email,
                            "client": client,
                            "week": week_str,
                            "value": val
                        })
                
                    if not hm_rows:
                        continue
                
                    hm_df = pd.DataFrame(hm_rows)
                    hm_weeks_sorted = sorted(hm_df["week"].unique(), key=_parse_week_sort_key_hm)
                
                    tick_text_labels = []
                    hm_hover_labels = []
                    for w in hm_weeks_sorted:
                        try:
                            start_date_str = w.split("/")[0]
                            dt = pd.to_datetime(start_date_str)
                            full_label = dt.strftime("%b %d, %Y").replace(" 0", " ")
                            hm_hover_labels.append(full_label)
                            month_year_label = dt.strftime("%b %Y")
                            tick_text_labels.append(month_year_label)
                        except Exception:
                            tick_text_labels.append(w)
                            hm_hover_labels.append(w)
                
                    talent_info = {}
                    for _, r in hm_df.iterrows():
                        tn = r["talent_name"]
                        if tn not in talent_info:
                            talent_info[tn] = {"client": r["client"], "values": []}
                        if r["value"] is not None:
                            talent_info[tn]["values"].append(r["value"])
                
                    talent_avgs = {tn: (np.mean(info["values"]) if info["values"] else 0) for tn, info in talent_info.items()}
                
                    if hm_sort_by == "Client Group":
                        sorted_talents = sorted(talent_info.keys(), key=lambda t: (talent_info[t]["client"], t))
                    elif hm_sort_by == "Average Score (Best First)":
                        sorted_talents = sorted(talent_info.keys(), key=lambda t: -talent_avgs[t])
                    elif hm_sort_by == "Average Score (Worst First)":
                        sorted_talents = sorted(talent_info.keys(), key=lambda t: talent_avgs[t])
                    else:
                        sorted_talents = sorted(talent_info.keys())
                
                    sorted_talents_display = list(reversed(sorted_talents))
                    z_matrix = []
                    text_matrix = []
                
                    for talent in sorted_talents_display:
                        row_vals = []
                        row_texts = []
                        for week in hm_weeks_sorted:
                            match = hm_df[(hm_df["talent_name"] == talent) & (hm_df["week"] == week)]
                            if not match.empty:
                                v = match.iloc[0]["value"]
                                if pd.notna(v):
                                    row_vals.append(v)
                                    if heatmap_metric == "Self Rating":
                                        row_texts.append(f"{v/20:.1f}")
                                    else:
                                        row_texts.append(f"{int(v)}")
                                else:
                                    row_vals.append(None)
                                    row_texts.append("—")
                            else:
                                row_vals.append(None)
                                row_texts.append("—")
                        z_matrix.append(row_vals)
                        text_matrix.append(row_texts)
                
                    if hm_sort_by == "Client Group":
                        y_labels = []
                        for talent in sorted_talents_display:
                            cl = talent_info[talent]["client"]
                            short_client = cl[:12] if len(cl) > 12 else cl
                            y_labels.append(f"{short_client} │ {talent}")
                    else:
                        y_labels = sorted_talents_display
                
                    custom_colorscale = [
                        [0.0, "#b91c1c"],
                        [0.25, "#dc6b4a"],
                        [0.4, "#f59e0b"],
                        [0.5, "#fbbf24"],
                        [0.65, "#84cc16"],
                        [0.8, "#22c55e"],
                        [1.0, "#15803d"],
                    ]
                
                    if heatmap_metric == "Self Rating":
                        zmin, zmax = 0, 100
                        colorbar_title = "Rating (norm.)"
                    elif heatmap_metric == "Ticket Completion %":
                        zmin, zmax = 40, 120
                        colorbar_title = "Completion %"
                    elif heatmap_metric == "QA Pass Rate":
                        zmin, zmax = 50, 100
                        colorbar_title = "QA %"
                    elif heatmap_metric == "Growth Score":
                        zmin, zmax = 0, 80
                        colorbar_title = "Growth"
                    else:
                        zmin, zmax = 30, 90
                        colorbar_title = "Composite"
                
                    hover_matrix = [hm_hover_labels for _ in range(len(y_labels))]
                
                    n_cols = len(hm_weeks_sorted)
                    if n_cols <= 15:
                        t_size = 11
                        col_px = 70
                    elif n_cols <= 25:
                        t_size = 10
                        col_px = 62
                    elif n_cols <= 40:
                        t_size = 9
                        col_px = 56
                    else:
                        t_size = 8
                        col_px = 50
                    x_gap = 3
                
                    fig_heatmap = go.Figure(data=go.Heatmap(
                        z=z_matrix,
                        x=hm_weeks_sorted,
                        y=y_labels,
                        text=text_matrix if hm_show_values else None,
                        texttemplate="%{text}" if hm_show_values else None,
                        textfont={"size": t_size, "color": "#ffffff", "family": "Montserrat, sans-serif"},
                        colorscale=custom_colorscale,
                        zmin=zmin,
                        zmax=zmax,
                        xgap=x_gap,
                        ygap=3,
                        customdata=hover_matrix,
                        colorbar=dict(
                            title=dict(text=colorbar_title, font=dict(size=12)),
                            thickness=15,
                            len=0.5,
                            tickfont=dict(size=10),
                        ),
                        hovertemplate=(
                            "<b>%{y}</b><br>"
                            "Week: %{customdata}<br>"
                            f"{heatmap_metric}: " + "%{text}<br>"
                            "<extra></extra>"
                        ),
                    ))
                
                    n_talents = len(sorted_talents_display)
                    row_height = max(36, min(54, 700 // max(n_talents, 1)))
                    chart_height = max(450, n_talents * row_height + 140)
                    chart_width = max(900, n_cols * col_px + 300)
                
                    fig_heatmap.update_layout(
                        xaxis=dict(
                            title="",
                            side="top",
                            type="category",
                            tickmode="array",
                            tickvals=hm_weeks_sorted,
                            ticktext=tick_text_labels,
                            tickangle=-45,
                            tickfont=dict(size=10, family="Montserrat, sans-serif"),
                        ),
                        yaxis=dict(
                            title="",
                            tickfont=dict(size=11, family="Montserrat, sans-serif"),
                            autorange="reversed",
                        ),
                        width=chart_width,
                        height=chart_height,
                        margin=dict(l=200, r=60, t=80, b=40),
                        plot_bgcolor="#fafafa",
                        paper_bgcolor="#ffffff",
                    )
                
                    if heatmap_metric == "Composite Score":
                        desc = "The overall health score combining ticket completion, QA pass rate, growth score, and self-rating."
                    elif heatmap_metric == "Ticket Completion %":
                        desc = "Percentage of assigned tickets that were completed each week."
                    elif heatmap_metric == "QA Pass Rate":
                        desc = "Percentage of tickets that passed Quality Assurance on the first attempt."
                    elif heatmap_metric == "Growth Score":
                        desc = "AI-calculated growth score evaluating skills improvement and feedback."
                    elif heatmap_metric == "Self Rating":
                        desc = "The talent's weekly self-reported satisfaction rating (1.0 - 5.0 scale normalized to 0-100)."
                    else:
                        desc = ""
                    
                    st.caption(f"**{heatmap_metric}**: {desc}")
                    
                    st.markdown(
                        '<div style="overflow-x:auto;max-width:100%;border:1px solid #e2e8f0;border-radius:12px;padding:8px 0;">',
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(fig_heatmap, use_container_width=True, key=f"heatmap_{metric_idx}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                    # Brief insight row for this metric
                    all_avg = {tn: talent_avgs[tn] for tn in sorted_talents if talent_avgs[tn] > 0}
                    if all_avg:
                        best_talent = max(all_avg, key=all_avg.get)
                        worst_talent = min(all_avg, key=all_avg.get)
                        team_avg = np.mean(list(all_avg.values()))
                        at_risk_count = len([tn for tn, avg in all_avg.items() if avg < 60])
                    
                        ic1, ic2, ic3, ic4 = st.columns(4)
                        with ic1:
                            st.metric("🏆 Top Performer", best_talent.split()[0], f"Avg: {all_avg[best_talent]:.0f}")
                        with ic2:
                            st.metric("⚠️ Needs Attention", worst_talent.split()[0], f"Avg: {all_avg[worst_talent]:.0f}")
                        with ic3:
                            st.metric("📊 Team Average", f"{team_avg:.0f}")
                        with ic4:
                            st.metric("🚨 At-Risk Count", f"{at_risk_count}", "below 60 avg" if at_risk_count > 0 else "All healthy", delta_color="inverse" if at_risk_count > 0 else "normal")
                
                    st.markdown("---")

def page_presentation_deck():
    if df is None or df.empty:
        st.warning("No data available.")
        st.stop()

    import plotly.graph_objects as go
    import numpy as np
    from collections import defaultdict
    
    def _parse_week_sort_key_pres(w):
        try:
            parts = w.split("-")
            return f"{parts[0]}-{parts[1]}-{parts[2].split('/')[0]}"
        except Exception:
            return w

    all_weeks = sorted(df["week"].dropna().unique(), key=_parse_week_sort_key_pres)
    trend_window_weeks = 6
    recent_weeks = all_weeks[-trend_window_weeks:] if len(all_weeks) > trend_window_weeks else all_weeks
    
    pres_df = df[df["week"].isin(recent_weeks)].copy()
    
    if pres_df.empty:
        st.warning(f"No data found for the last {trend_window_weeks} weeks.")
        st.stop()

    def _get_metrics(row):
        comp = row.get("tickets_completed")
        exp = row.get("tickets_expected")
        ticket_pct = min(100, float(comp) / float(exp) * 100) if (pd.notna(comp) and pd.notna(exp) and float(exp) > 0) else None
        
        qa = row.get("qa_first_pass_pct")
        qa_val = float(qa) if pd.notna(qa) else None
        
        rat = row.get("overall_rating")
        if pd.notna(rat):
            if isinstance(rat, str):
                s = rat.strip().lower()
                if s == "excellent": rat = 5.0
                elif s == "above average": rat = 4.0
                elif s == "average": rat = 3.0
                elif s == "below average": rat = 2.0
                elif s == "poor": rat = 1.0
                else:
                    try: rat = float(rat)
                    except: rat = None
            rat_val = float(rat) * 20 if rat is not None else None
        else:
            rat_val = None
            
        return pd.Series([ticket_pct, qa_val, rat_val])

    pres_df[["Ticket Completion %", "QA Pass Rate", "Self Rating"]] = pres_df.apply(_get_metrics, axis=1)
    
    def format_week_label(w):
        try:
            import datetime
            parts = w.split("-")
            month = int(parts[1])
            day = int(parts[2].split('/')[0])
            month_abbr = datetime.date(2000, month, 1).strftime('%b')
            return f"{month_abbr} {day}"
        except:
            return str(w)

    display_weeks = [format_week_label(w) for w in recent_weeks]

    # Broad, universally applicable business domains
    COMPETENCIES = {
        "Client & Support Ops": ["client", "communication", "meeting", "call", "email", "chat", "support", "customer", "respond", "ticket", "inquiry"],
        "Technical & Tooling": ["code", "fix", "bug", "technical", "development", "system", "tool", "software", "platform", "app", "api", "update", "script"],
        "Admin & Data": ["organize", "schedule", "calendar", "data", "entry", "document", "file", "report", "sheet", "record", "track", "manage"],
        "Strategy & Planning": ["strategy", "plan", "review", "roadmap", "process", "improvement", "goal", "research", "lead", "manage"],
        "Quality & Review": ["qa", "review", "test", "quality", "check", "feedback", "edit", "proofread", "audit", "verify"]
    }
    COMP_KEYS = list(COMPETENCIES.keys()) + ["General Execution"]

    def extract_competencies(text):
        if pd.isna(text) or not str(text).strip():
            return []
            
        words = set([w.strip(".,()!?:;'\"").lower() for w in str(text).split()])
        found_comps = []
        
        for comp, keywords in COMPETENCIES.items():
            for kw in keywords:
                if kw in words or any(w.startswith(kw) for w in words):
                    found_comps.append(comp)
                    break
                    
        return found_comps if found_comps else ["General Execution"]

    metrics_list = ["Ticket Completion %", "QA Pass Rate", "Self Rating"]
    metric_colors = {
        "Ticket Completion %": "#3b82f6", # blue
        "QA Pass Rate": "#22c55e",       # green
        "Self Rating": "#a855f7"         # purple
    }

    st.markdown("""
        <style>
            /* Make Streamlit's default top header scroll away */
            [data-testid="stHeader"] {
                position: absolute !important;
            }
            
            /* Remove the huge white space at the top of the app */
            .stAppViewBlockContainer, div[data-testid="stAppViewBlockContainer"] {
                padding-top: 0.5rem !important;
            }

            /* Add shadow to talent containers and enforce equal height */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.talent-shadow-box) {
                height: 100% !important;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
                border-radius: 12px !important;
                border: 1px solid #e2e8f0 !important;
                background-color: #ffffff !important;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                display: flex;
                flex-direction: column;
            }
            
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.talent-shadow-box):hover {
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
                transform: translateY(-2px);
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Collect all unique emails present in the recent weeks dataframe
    all_emails = [e for e in pres_df["email"].unique()]
    
    # Sort them by client, then by talent name to keep it organized
    all_emails.sort(key=lambda x: (TALENT_ROSTER.get(x, {}).get("client") or "Unassigned", name_by_email.get(x, display_name(x))))
    
    if not all_emails:
        st.info("No talent data to display.")
        st.stop()
        
    st.markdown(f"<h2 style='text-align: center; margin-top: 0px; margin-bottom: 30px; font-weight: 800; color: #0f172a;'>Performance Trends & Skill Matrix (Last {trend_window_weeks} Weeks)</h2>", unsafe_allow_html=True)
        
    # Process emails in pairs to create perfectly even rows
    for i in range(0, len(all_emails), 2):
        pair_emails = all_emails[i:i+2]
        
        # ALWAYS use 2 columns so the cards don't wildly stretch if it's the last odd item
        cols = st.columns(2)
        
        for col_idx, email in enumerate(pair_emails):
            with cols[col_idx]:
                with st.container(border=True):
                    st.markdown('<div class="talent-shadow-box" style="display:none;"></div>', unsafe_allow_html=True)
                    
                    talent_name = name_by_email.get(email, display_name(email))
                    client_name = TALENT_ROSTER.get(email, {}).get("client") or "Unassigned"
                    
                    talent_data = pres_df[pres_df["email"] == email]
                    if talent_data.empty: continue
                    
                    # Layout: Talent Name + Glowing Client Badge
                    header_html = f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #334155; font-weight: 700;">👤 {talent_name}</h4>
                        <div style="
                            padding: 3px 10px; 
                            border-radius: 20px; 
                            font-size: 11px; 
                            font-weight: 700; 
                            color: #0ea5e9; 
                            background-color: rgba(14, 165, 233, 0.05);
                            border: 1px solid rgba(14, 165, 233, 0.2);
                            box-shadow: 0 0 10px rgba(14, 165, 233, 0.4);
                            text-shadow: 0 0 4px rgba(14, 165, 233, 0.2);
                        ">🏢 {client_name}</div>
                    </div>
                    """
                    st.markdown(header_html, unsafe_allow_html=True)
                    
                    sub_c1, sub_c2 = st.columns([1, 1.1])
                    
                    # --- 1. Line Chart Data ---
                    talent_data_line = talent_data.set_index("week")
                    talent_data_avg = talent_data_line.groupby("week")[metrics_list].mean()
                    talent_data_avg = talent_data_avg.reindex(recent_weeks)
                    
                    fig_t = go.Figure()
                    for metric in metrics_list:
                        fig_t.add_trace(go.Scatter(
                            x=display_weeks, y=talent_data_avg[metric],
                            mode='lines+markers',
                            name=metric.replace(' %', '').replace(' Rate', ''),
                            line=dict(color=metric_colors[metric], width=3),
                            marker=dict(size=8)
                        ))
                    fig_t.update_layout(
                        title=dict(text="Trends", font=dict(size=12)),
                        height=180,
                        yaxis=dict(range=[0, 105]),
                        margin=dict(l=20, r=5, t=30, b=10),
                        plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=8)),
                        xaxis=dict(tickfont=dict(size=9)),
                    )
                    
                    # --- 2. Skill Matrix Data ---
                    week_data = {}
                    for w in recent_weeks:
                        w_rows = talent_data[talent_data["week"] == w]
                        if w_rows.empty:
                            week_data[w] = {"score": 0, "comps": []}
                        else:
                            row = w_rows.iloc[0]
                            score = float(row.get("growth_score")) if pd.notna(row.get("growth_score")) else 0
                            txt = str(row.get("key_achievements")).strip() if pd.notna(row.get("key_achievements")) else ""
                            comps = extract_competencies(txt) if txt else []
                            week_data[w] = {"score": score, "comps": comps}
                                    
                    z_matrix = []
                    c_text_matrix = []
                    
                    for comp in COMP_KEYS:
                        row_z = []
                        row_text = []
                        for w in recent_weeks:
                            d = week_data[w]
                            if comp in d["comps"]:
                                row_z.append(1)
                                row_text.append("✓")
                            else:
                                row_z.append(0)
                                row_text.append("")
                        z_matrix.append(row_z)
                        c_text_matrix.append(row_text)
                        
                    check_colorscale = [[0.0, "#f8fafc"], [1.0, "#10b981"]]
                    
                    fig_hm = go.Figure(data=go.Heatmap(
                        z=z_matrix, x=display_weeks, y=COMP_KEYS,
                        text=c_text_matrix, texttemplate="%{text}",
                        textfont={"size": 12, "color": "#ffffff"},
                        hoverinfo="none",
                        colorscale=check_colorscale, zmin=0, zmax=1,
                        xgap=2, ygap=2, showscale=False
                    ))
                    
                    fig_hm.update_layout(
                        title=dict(text="Matrix", font=dict(size=12)),
                        height=180,
                        margin=dict(l=100, r=5, t=30, b=10),
                        xaxis=dict(side="top", tickfont=dict(size=9), categoryorder='array', categoryarray=display_weeks),
                        yaxis=dict(tickfont=dict(size=9, weight="bold"), autorange="reversed", categoryorder='array', categoryarray=COMP_KEYS),
                        plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)",
                    )
                    
                    with sub_c1:
                        st.plotly_chart(fig_t, use_container_width=True, key=f"t_{email}")
                    with sub_c2:
                        st.plotly_chart(fig_hm, use_container_width=True, key=f"hm_{email}")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

def page_client_portfolio():
    import re
    import plotly.graph_objects as go

    st.title("Client Portfolio Report")
    st.caption("Simple client and talent metrics for the past 2 months of check-in data")

    with st.expander("Merge duplicate Telegram emails", expanded=False):
        st.caption("Map an alternate submission email to the person's primary registered email. The app will merge their rows on refresh.")
        alias_options = sorted(people, key=lambda e: name_by_email.get(e, display_name(e)))
        with st.form("email_alias_form"):
            alias_col, primary_col, submit_col = st.columns([2, 2, 1])
            with alias_col:
                alias_email = st.text_input("Alternate email used in Telegram", placeholder="alternate@example.com")
            with primary_col:
                primary_email = st.selectbox(
                    "Merge into primary person",
                    alias_options,
                    format_func=lambda e: f"{name_by_email.get(e, display_name(e))} ({e})",
                )
            with submit_col:
                st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
                merge_submitted = st.form_submit_button("Merge", use_container_width=True)

        if merge_submitted:
            alias_clean = _clean_email_value(alias_email)
            primary_clean = _clean_email_value(primary_email)
            if not alias_clean:
                st.warning("Add the alternate email first.")
            elif alias_clean == primary_clean:
                st.warning("Alternate email and primary email are the same.")
            else:
                save_manual_email_alias(alias_clean, primary_clean)
                st.cache_data.clear()
                st.success(f"Saved alias: {alias_clean} -> {primary_clean}")
                st.rerun()

        manual_aliases = load_manual_email_aliases()
        if manual_aliases:
            alias_rows = [
                {
                    "Alternate Email": alias,
                    "Primary Email": primary,
                    "Primary Talent": display_name(primary),
                }
                for alias, primary in sorted(manual_aliases.items())
            ]
            st.dataframe(pd.DataFrame(alias_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No manual aliases saved yet.")

    def _safe_num(v):
        try:
            f = float(v)
            return None if pd.isna(f) else f
        except (TypeError, ValueError):
            return None

    def _fmt_pct(v):
        return "No data" if v is None or pd.isna(v) else f"{v:.0f}%"

    def _fmt_num(v):
        return "No data" if v is None or pd.isna(v) else f"{v:.1f}"

    def _status_from_pct(v, warn=70, ok=85):
        if v is None or pd.isna(v):
            return "No data"
        if v >= ok:
            return "On track"
        if v >= warn:
            return "Watch"
        return "At risk"

    def _status_color(status: str) -> str:
        return {
            "On track": "#16a34a",
            "Watch": "#f59e0b",
            "At risk": "#dc2626",
            "No data": "#94a3b8",
        }.get(str(status), "#94a3b8")

    def _chart_layout(fig, height=260, showlegend=False):
        fig.update_layout(
            height=height,
            margin=dict(l=8, r=8, t=36, b=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#ffffff",
            font=dict(family="Montserrat, sans-serif", size=11, color="#334155"),
            showlegend=showlegend,
        )
        return fig

    def _split_achievement_items(text: str) -> list[str]:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if not clean or clean.lower() == "nan":
            return []
        raw_items = re.split(r"(?:\n+|;| • | \* |- )", str(text or ""))
        items = [re.sub(r"\s+", " ", item).strip(" .:-") for item in raw_items]
        items = [item for item in items if len(item) >= 18]
        if items:
            return items[:4]
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        return [s.strip() for s in sentences if len(s.strip()) >= 18][:4] or [clean[:220]]

    def _achievement_theme(text: str) -> str:
        tags = extract_achievements_tags(str(text or ""))
        return tags[0] if tags else "General Execution"

    def _achievement_complexity(text: str) -> tuple[int, str, list[str], str]:
        lower = str(text or "").lower()
        words = re.findall(r"[a-zA-Z]+", lower)
        item_count = len(_split_achievement_items(text))
        numbers = len(re.findall(r"\b\d+\b", lower))
        score = 10
        score += min(20, len(words) // 12 * 4)
        score += min(15, item_count * 5)
        score += min(10, numbers * 2)

        signals: list[str] = []
        scoring_notes = [
            f"text detail {min(20, len(words) // 12 * 4)}/20",
            f"task breadth {min(15, item_count * 5)}/15",
            f"specific metrics {min(10, numbers * 2)}/10",
        ]
        signal_groups = [
            (["built", "implemented", "developed", "created", "delivered", "shipped"], "delivery", "delivery verbs +8"),
            (["designed", "architecture", "strategy", "framework", "schema", "model"], "design/architecture", "design/architecture +8"),
            (["migrated", "integrated", "refactored", "optimized", "automated", "pipeline"], "technical depth", "technical depth +8"),
            (["production", "deploy", "release", "handover"], "release impact", "release impact +8"),
            (["investigated", "root cause", "resolved", "debug", "analysis", "research"], "problem solving", "problem solving +8"),
            (["documentation", "runbook", "knowledge base", "training", "guide"], "knowledge transfer", "knowledge transfer +8"),
            (["cross-team", "multiple teams", "stakeholder", "client", "demo", "customer", "user acceptance", "uat"], "client/project exposure", "client/project exposure +8"),
        ]
        for keywords, label, note in signal_groups:
            if any(k in lower for k in keywords):
                signals.append(label)
                scoring_notes.append(note)
                score += 8

        score = int(max(0, min(100, score)))
        if score >= 75:
            level = "Strategic / complex"
        elif score >= 55:
            level = "Advanced delivery"
        elif score >= 35:
            level = "Solid execution"
        else:
            level = "Routine / unclear"
        return score, level, signals[:4], "; ".join(scoring_notes)

    def _client_exposure_score(text: str) -> tuple[int, str]:
        lower = str(text or "").lower()
        score = 0
        if any(k in lower for k in ["client", "customer", "demo", "standup", "clarification", "product owner", "tech lead"]):
            score += 40
        if any(k in lower for k in ["stakeholder", "executive", "end user", "user acceptance", "uat", "handover", "feedback"]):
            score += 40
        if any(k in lower for k in ["cross-team", "multiple teams", "organization", "migration", "architecture"]):
            score += 20
        score = min(100, score)
        if score >= 70:
            label = "High client/stakeholder exposure"
        elif score >= 35:
            label = "Client/team interface"
        else:
            label = "Internal/team task"
        return score, label

    def _submission_status(last_seen, latest_seen) -> str:
        if pd.isna(last_seen) or pd.isna(latest_seen):
            return "No dated history"
        days = (latest_seen - last_seen).days
        if days > 28:
            return "Stopped filling"
        if days > 14:
            return "Missed recent weeks"
        return "Currently filling"

    def _talent_group(first_seen, latest_seen) -> str:
        if pd.isna(first_seen) or pd.isna(latest_seen):
            return "Group A"
        months_active = (latest_seen - first_seen).days / 30.44
        return "Group E" if months_active > 6 else "Group A"

    def _group_expectation(group: str) -> str:
        if group == "Group E":
            return "Expected context: medium task complexity and regular client/project-team interface."
        if group == "Group I":
            return "Expected context: high stakeholder exposure and large, multi-quarter or cross-organization initiatives."
        return "Expected context: team-level tasks, small fixes, low client exposure."

    def _level_context(row) -> str:
        group = str(row.get("talent_group", "Group A"))
        complexity = _safe_num(row.get("achievement_complexity")) or 0
        exposure = _safe_num(row.get("client_exposure_score")) or 0
        if group == "Group E":
            if complexity >= 55 or exposure >= 35:
                return "Aligned for Group E"
            return "Below Group E expectation"
        if group == "Group I":
            if complexity >= 75 and exposure >= 70:
                return "Aligned for Group I"
            return "Below Group I expectation"
        if complexity >= 55 or exposure >= 35:
            return "Stretching beyond Group A"
        return "Aligned for Group A"

    def _group_badge(group: str) -> str:
        group_clean = str(group or "Group A").strip()
        return {"Group A": "A", "Group E": "E", "Group I": "I"}.get(group_clean, "A")

    def _achievement_focus(text: str) -> str:
        items = _split_achievement_items(text)
        if not items:
            return "No achievement text"
        first = items[0]
        return first if len(first) <= 180 else first[:177].rstrip() + "..."

    def _achievement_tokens(text: str) -> set[str]:
        stop_words = {
            "the", "and", "for", "with", "that", "this", "week", "was", "were", "have",
            "has", "had", "able", "been", "from", "into", "about", "also", "work",
            "worked", "working", "completed", "task", "tasks", "ticket", "tickets",
        }
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", str(text or "").lower())
            if token not in stop_words
        }

    def _achievement_similarity(current: str, previous: str) -> float | None:
        current_tokens = _achievement_tokens(current)
        previous_tokens = _achievement_tokens(previous)
        if not current_tokens or not previous_tokens:
            return None
        return round(len(current_tokens & previous_tokens) / len(current_tokens | previous_tokens) * 100, 1)

    def _relation_label(similarity: float | None, current_theme: str, previous_theme: str | None) -> str:
        if similarity is None or not previous_theme:
            return "First visible update"
        if similarity >= 45:
            return "Same / continued work"
        if similarity >= 20:
            return "Related but shifted"
        return "Completely different work"

    def _relation_short(label: str) -> str:
        return {
            "First visible update": "F",
            "Same / continued work": "S",
            "Related but shifted": "R",
            "Completely different work": "D",
        }.get(str(label), "Work")

    def _change_sentence(row) -> str:
        relation = str(row.get("achievement_relation", ""))
        previous = str(row.get("previous_focus", "") or "").strip()
        current = str(row.get("achievement_focus", "") or "").strip()
        if relation == "First visible update" or not previous or previous == "No achievement text":
            return "First visible update in this report window."
        if relation == "Same / continued work":
            return "Continues the prior focus area."
        if relation == "Related but shifted":
            return "Related to prior work, but the focus shifted."
        if relation == "Completely different work":
            return "Started a completely different work area compared with the previous update."
        if current and previous:
            return "Different from the previous update."
        return relation or "No comparison available."

    def _week_start(w):
        try:
            return pd.to_datetime(str(w).split("/")[0].strip())
        except Exception:
            return pd.NaT

    def _report_metric(row):
        comp = _safe_num(row.get("tickets_completed"))
        exp = _safe_num(row.get("tickets_expected"))
        ticket_pct = min(100, comp / exp * 100) if comp is not None and exp and exp > 0 else None
        qa = _safe_num(row.get("qa_first_pass_pct"))
        growth = _safe_num(row.get("growth_score"))
        rating = _safe_num(row.get("overall_rating"))
        rating_pct = rating * 20 if rating is not None and rating <= 5 else rating
        parts = [p for p in [ticket_pct, qa, growth, rating_pct] if p is not None and not pd.isna(p)]
        return round(sum(parts) / len(parts), 1) if parts else None

    report_df = df.copy()
    report_df["email"] = report_df["email"].astype(str).str.strip().str.lower()
    ensure_unassigned_talents(report_df)
    report_df["client"] = report_df["email"].map(lambda e: TALENT_ROSTER.get(e, {}).get("client") or "Unassigned")
    report_df["talent"] = report_df["email"].map(lambda e: name_by_email.get(e, display_name(e)))
    report_df["week_start"] = report_df["week"].map(_week_start) if "week" in report_df.columns else pd.NaT
    if "timestamp" in report_df.columns:
        report_df["submitted_at"] = pd.to_datetime(report_df["timestamp"], errors="coerce").dt.tz_localize(None)
    else:
        report_df["submitted_at"] = pd.NaT
    report_df["report_date"] = report_df["submitted_at"].fillna(report_df["week_start"])
    report_df["_row_id"] = range(len(report_df))

    if "key_achievements" in report_df.columns:
        historical_metrics = report_df["key_achievements"].map(_achievement_complexity)
        report_df["_historical_theme"] = report_df["key_achievements"].map(_achievement_theme)
        report_df["_historical_complexity"] = historical_metrics.map(lambda x: x[0])
        historical_sorted = report_df.sort_values(["email", "week_start", "report_date"]).copy()
        historical_sorted["_previous_achievement_all"] = historical_sorted.groupby("email")["key_achievements"].shift(1)
        historical_sorted["_previous_theme_all"] = historical_sorted.groupby("email")["_historical_theme"].shift(1)
        historical_sorted["_previous_complexity_all"] = historical_sorted.groupby("email")["_historical_complexity"].shift(1)
        historical_previous = historical_sorted[[
            "_row_id",
            "_previous_achievement_all",
            "_previous_theme_all",
            "_previous_complexity_all",
        ]]
    else:
        historical_previous = pd.DataFrame(columns=[
            "_row_id",
            "_previous_achievement_all",
            "_previous_theme_all",
            "_previous_complexity_all",
        ])

    latest_date = report_df["report_date"].dropna().max()
    if pd.isna(latest_date):
        st.warning("No dated check-in data available for the portfolio report.")
        st.stop()

    history_rows = []
    dated_history = report_df.dropna(subset=["report_date"]).copy()
    for email, hdf in dated_history.groupby("email", dropna=False):
        first_seen = hdf["report_date"].min()
        last_seen = hdf["report_date"].max()
        active_days = (latest_date - first_seen).days if pd.notna(first_seen) else None
        expected_weeks = max(1, int(((last_seen - first_seen).days if pd.notna(first_seen) and pd.notna(last_seen) else 0) / 7) + 1)
        weeks_submitted = hdf["week_start"].nunique() if "week_start" in hdf.columns else len(hdf)
        fill_rate = min(100, weeks_submitted / expected_weeks * 100) if expected_weeks else None
        history_rows.append({
            "email": email,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "months_active": None if active_days is None else round(active_days / 30.44, 1),
            "talent_group": _talent_group(first_seen, latest_date),
            "submission_status": _submission_status(last_seen, latest_date),
            "historical_weeks_submitted": weeks_submitted,
            "historical_fill_rate": None if fill_rate is None else round(fill_rate, 1),
        })
    talent_history = pd.DataFrame(history_rows)

    cutoff_date = latest_date - pd.DateOffset(months=2)
    period_df = report_df[report_df["report_date"] >= cutoff_date].copy()
    if period_df.empty:
        st.warning("No check-in data found in the past 2 months.")
        st.stop()

    period_df["ticket_pct"] = period_df.apply(
        lambda r: min(100, float(r["tickets_completed"]) / float(r["tickets_expected"]) * 100)
        if pd.notna(r.get("tickets_completed")) and pd.notna(r.get("tickets_expected")) and float(r.get("tickets_expected")) > 0
        else None,
        axis=1,
    )
    period_df["composite_score_report"] = period_df.apply(_report_metric, axis=1)
    if not talent_history.empty:
        period_df = period_df.merge(talent_history, on="email", how="left")
    else:
        period_df["talent_group"] = "Group A"
        period_df["submission_status"] = "No dated history"
        period_df["months_active"] = None
        period_df["historical_weeks_submitted"] = None
        period_df["historical_fill_rate"] = None
    if not historical_previous.empty and "_row_id" in period_df.columns:
        period_df = period_df.merge(historical_previous, on="_row_id", how="left")
    else:
        period_df["_previous_achievement_all"] = ""
        period_df["_previous_theme_all"] = None
        period_df["_previous_complexity_all"] = None
    period_df["achievement_theme"] = period_df["key_achievements"].map(_achievement_theme) if "key_achievements" in period_df.columns else "General Execution"
    if "key_achievements" in period_df.columns:
        achievement_metrics = period_df["key_achievements"].map(_achievement_complexity)
        period_df["achievement_complexity"] = achievement_metrics.map(lambda x: x[0])
        period_df["achievement_level"] = achievement_metrics.map(lambda x: x[1])
        period_df["achievement_signals"] = achievement_metrics.map(lambda x: ", ".join(x[2]) if x[2] else "limited detail")
        period_df["complexity_scoring_notes"] = achievement_metrics.map(lambda x: x[3])
        exposure_metrics = period_df["key_achievements"].map(_client_exposure_score)
        period_df["client_exposure_score"] = exposure_metrics.map(lambda x: x[0])
        period_df["client_exposure_level"] = exposure_metrics.map(lambda x: x[1])
        period_df["achievement_focus"] = period_df["key_achievements"].map(_achievement_focus)
    else:
        period_df["achievement_complexity"] = 0
        period_df["achievement_level"] = "No data"
        period_df["achievement_signals"] = "No data"
        period_df["complexity_scoring_notes"] = "No achievement text"
        period_df["client_exposure_score"] = 0
        period_df["client_exposure_level"] = "No data"
        period_df["achievement_focus"] = "No achievement text"

    period_df = period_df.sort_values(["email", "week_start", "report_date"]).copy()
    period_df["previous_achievement"] = period_df["_previous_achievement_all"] if "key_achievements" in period_df.columns else ""
    period_df["previous_theme"] = period_df["_previous_theme_all"]
    period_df["previous_complexity"] = period_df["_previous_complexity_all"]
    period_df["previous_focus"] = period_df["previous_achievement"].map(_achievement_focus)
    period_df["achievement_similarity"] = period_df.apply(
        lambda r: _achievement_similarity(r.get("key_achievements", ""), r.get("previous_achievement", "")),
        axis=1,
    )
    period_df["achievement_novelty"] = period_df["achievement_similarity"].map(lambda v: None if v is None or pd.isna(v) else round(100 - v, 1))
    period_df["complexity_change"] = period_df["achievement_complexity"] - period_df["previous_complexity"]
    period_df["achievement_relation"] = period_df.apply(
        lambda r: _relation_label(r.get("achievement_similarity"), r.get("achievement_theme"), r.get("previous_theme")),
        axis=1,
    )
    period_df["relation_short"] = period_df["achievement_relation"].map(_relation_short)
    period_df["change_summary"] = period_df.apply(_change_sentence, axis=1)
    period_df["level_context"] = period_df.apply(_level_context, axis=1)
    period_df["group_expectation"] = period_df["talent_group"].map(_group_expectation)

    start_label = cutoff_date.strftime("%b %-d, %Y")
    end_label = latest_date.strftime("%b %-d, %Y")
    st.markdown(f"**Reporting period:** {start_label} to {end_label}")

    total_clients = period_df["client"].nunique()
    total_talents = period_df["email"].nunique()
    total_submissions = len(period_df)
    avg_ticket = period_df["ticket_pct"].dropna().mean()
    avg_qa = period_df["qa_first_pass_pct"].dropna().mean() if "qa_first_pass_pct" in period_df.columns else None

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Clients", total_clients)
    k2.metric("Talents", total_talents)
    k3.metric("Check-ins", total_submissions)
    k4.metric("Avg Ticket Completion", _fmt_pct(avg_ticket))
    k5.metric("Avg QA First-Pass", _fmt_pct(avg_qa))

    st.markdown("---")
    context_cols = st.columns([1.1, 1])
    with context_cols[0]:
        st.subheader("Task Complexity Score")
        st.table(pd.DataFrame([
            {"Metric used": "Text detail", "Max points": 20, "Meaning": "Longer, more specific updates usually explain more complex work."},
            {"Metric used": "Task breadth", "Max points": 15, "Meaning": "Multiple clear work items increase the score."},
            {"Metric used": "Specific metrics", "Max points": 10, "Meaning": "Numbers, counts, or measurable scope increase confidence."},
            {"Metric used": "Complexity signals", "Max points": 56, "Meaning": "Delivery, architecture, integration, release, problem solving, knowledge transfer, and client/project exposure signals add 8 points each."},
        ]))
    with context_cols[1]:
        st.subheader("Talent Level Context")
        st.table(pd.DataFrame([
            {"Group": "Group A", "Expected work": "Team-level tasks, fixes, low client exposure."},
            {"Group": "Group E", "Expected work": "Medium complexity work with regular client/project-team interface."},
            {"Group": "Group I", "Expected work": "High stakeholder exposure and large cross-team initiatives. No Group I talents yet."},
        ]))

    st.markdown("---")
    st.subheader("Talent Detail by Client")


    client_talent_counts = period_df.groupby("client", dropna=False)["email"].nunique().to_dict()
    clients_sorted = sorted(
        period_df["client"].dropna().unique().tolist(),
        key=lambda c: (-client_talent_counts.get(c, 0), c == "Unassigned", str(c)),
    )
    selected_clients = st.pills(
        "Clients to show",
        clients_sorted,
        selection_mode="multi",
        default=clients_sorted,
        key="portfolio_report_clients",
    )
    selected_clients = selected_clients or clients_sorted
    relation_colors = {
        "Same / continued work": "#2563eb",
        "Related but shifted": "#7c3aed",
        "Completely different work": "#dc2626",
        "First visible update": "#94a3b8",
    }

    for client in selected_clients:
        cdf = period_df[period_df["client"] == client].copy()
        if cdf.empty:
            continue

        rows = []
        for email, tdf in cdf.groupby("email", dropna=False):
            ticket_rows = tdf.dropna(subset=["tickets_completed", "tickets_expected"])
            ticket_rows = ticket_rows[ticket_rows["tickets_expected"] > 0]
            ticket_pct = (ticket_rows["tickets_completed"].sum() / ticket_rows["tickets_expected"].sum() * 100) if len(ticket_rows) else None
            qa_pct = tdf["qa_first_pass_pct"].dropna().mean() if "qa_first_pass_pct" in tdf.columns else None
            score = tdf["composite_score_report"].dropna().mean()
            latest_submit = tdf["report_date"].dropna().max()
            rows.append({
                "Talent": name_by_email.get(email, display_name(email)),
                "Email": email,
                "Check-ins": len(tdf),
                "Weeks": tdf["week"].nunique() if "week" in tdf.columns else 0,
                "Tickets Done": int(ticket_rows["tickets_completed"].sum()) if len(ticket_rows) else 0,
                "Tickets Expected": int(ticket_rows["tickets_expected"].sum()) if len(ticket_rows) else 0,
                "Ticket Completion": _fmt_pct(ticket_pct),
                "Ticket Completion Value": round(ticket_pct, 1) if ticket_pct is not None and not pd.isna(ticket_pct) else None,
                "QA First-Pass": _fmt_pct(qa_pct),
                "QA First-Pass Value": round(qa_pct, 1) if qa_pct is not None and not pd.isna(qa_pct) else None,
                "Avg Score": _fmt_num(score),
                "Avg Score Value": round(score, 1) if score is not None and not pd.isna(score) else None,
                "Status": _status_from_pct(score),
                "Talent Group": tdf["talent_group"].dropna().iloc[-1] if "talent_group" in tdf.columns and not tdf["talent_group"].dropna().empty else "Group A",
                "Months Active": tdf["months_active"].dropna().iloc[-1] if "months_active" in tdf.columns and not tdf["months_active"].dropna().empty else None,
                "Filling Status": tdf["submission_status"].dropna().iloc[-1] if "submission_status" in tdf.columns and not tdf["submission_status"].dropna().empty else "No dated history",
                "Latest Check-in": latest_submit.strftime("%b %-d") if pd.notna(latest_submit) else "No date",
            })

        talent_table = pd.DataFrame(rows).sort_values(["Status", "Talent"])
        with st.expander(f"{client} - {len(rows)} talent(s), {len(cdf)} check-ins", expanded=True):
            client_start = cdf["week_start"].dropna().min()
            client_end = cdf["week_start"].dropna().max()
            client_week_count = cdf["week_start"].dropna().nunique()
            client_story = cdf.dropna(subset=["week_start"]).copy()
            client_story["Week"] = client_story["week_start"].dt.strftime("%b %-d")
            client_week_order = client_story.sort_values("week_start")["Week"].drop_duplicates().tolist()
            client_talent_order = client_story.groupby("talent")["achievement_complexity"].mean().sort_values(ascending=False).index.tolist()
            client_group_by_talent = (
                client_story.sort_values("report_date")
                .groupby("talent")["talent_group"]
                .last()
                .to_dict()
            )
            client_talent_labels = {
                talent_name: f"{talent_name}<sup>{_group_badge(client_group_by_talent.get(talent_name))}</sup>"
                for talent_name in client_talent_order
            }

            client_timeline = client_story.pivot_table(
                index="talent",
                columns="Week",
                values="achievement_complexity",
                aggfunc="mean",
            ).reindex(index=client_talent_order, columns=client_week_order)
            client_focus = client_story.pivot_table(
                index="talent",
                columns="Week",
                values="achievement_focus",
                aggfunc=lambda values: " | ".join(str(v) for v in values if str(v).strip())[:320],
            ).reindex(index=client_talent_order, columns=client_week_order)
            client_relation = client_story.pivot_table(
                index="talent",
                columns="Week",
                values="achievement_relation",
                aggfunc=lambda values: " / ".join(sorted(set(str(v) for v in values if str(v).strip()))),
            ).reindex(index=client_talent_order, columns=client_week_order)
            client_relation_short = client_story.pivot_table(
                index="talent",
                columns="Week",
                values="relation_short",
                aggfunc=lambda values: " / ".join(sorted(set(str(v) for v in values if str(v).strip()))),
            ).reindex(index=client_talent_order, columns=client_week_order)
            client_theme = client_story.pivot_table(
                index="talent",
                columns="Week",
                values="achievement_theme",
                aggfunc=lambda values: " / ".join(sorted(set(str(v) for v in values if str(v).strip()))),
            ).reindex(index=client_talent_order, columns=client_week_order)

            client_hover = []
            client_labels = []
            for talent_name in client_timeline.index:
                row_hover = []
                row_labels = []
                for week_label in client_timeline.columns:
                    complexity_val = client_timeline.loc[talent_name, week_label]
                    focus_val = client_focus.loc[talent_name, week_label] if talent_name in client_focus.index and week_label in client_focus.columns else ""
                    relation_val = client_relation.loc[talent_name, week_label] if talent_name in client_relation.index and week_label in client_relation.columns else ""
                    relation_short_val = client_relation_short.loc[talent_name, week_label] if talent_name in client_relation_short.index and week_label in client_relation_short.columns else ""
                    theme_val = client_theme.loc[talent_name, week_label] if talent_name in client_theme.index and week_label in client_theme.columns else ""
                    if pd.isna(complexity_val):
                        row_hover.append("No update")
                        row_labels.append("")
                    else:
                        row_hover.append(
                            f"<b>{talent_name}</b><br>{week_label}<br>"
                            f"Task Complexity: {complexity_val:.0f}<br>"
                            f"Theme: {theme_val}<br>"
                            f"Relation: {relation_val}<br>"
                            f"Focus: {focus_val}"
                        )
                        row_labels.append(f"{complexity_val:.0f}<br>{relation_short_val}")
                client_hover.append(row_hover)
                client_labels.append(row_labels)

            client_timeline_fig = go.Figure(go.Heatmap(
                z=client_timeline.values,
                x=client_timeline.columns,
                y=[client_talent_labels.get(talent_name, talent_name) for talent_name in client_timeline.index],
                text=client_labels,
                customdata=client_hover,
                texttemplate="%{text}",
                textfont=dict(size=10, color="#0f172a"),
                hovertemplate="%{customdata}<extra></extra>",
                colorscale=[[0, "#f8fafc"], [0.35, "#bfdbfe"], [0.65, "#60a5fa"], [1, "#1d4ed8"]],
                zmin=0,
                zmax=100,
                colorbar=dict(title="Task Complexity"),
                xgap=2,
                ygap=2,
            ))
            client_timeline_fig.update_layout(title=dict(text="Task Complexity + Work Continuity", font=dict(size=13)))
            client_timeline_fig.update_xaxes(title=None, side="top", tickangle=0, tickfont=dict(size=10), automargin=True)
            client_timeline_fig.update_yaxes(title=None, automargin=True)
            _chart_layout(client_timeline_fig, height=max(320, 120 + len(client_timeline.index) * 42))
            client_timeline_fig.update_layout(margin=dict(l=8, r=8, t=64, b=20))

            client_relation_fig = go.Figure()
            relation_order = [
                "Same / continued work",
                "Related but shifted",
                "Completely different work",
                "First visible update",
            ]
            for relation in relation_order:
                rdf = client_story[client_story["achievement_relation"] == relation].copy()
                if rdf.empty:
                    continue
                rdf = rdf.sort_values(["week_start", "talent"])
                client_relation_fig.add_trace(go.Scatter(
                    x=rdf["week_start"],
                    y=[client_talent_labels.get(talent_name, talent_name) for talent_name in rdf["talent"]],
                    name=relation,
                    mode="markers+text",
                    marker=dict(
                        color=relation_colors.get(relation, "#64748b"),
                        size=22,
                        line=dict(color="#ffffff", width=1),
                    ),
                    text=rdf["relation_short"],
                    textposition="middle center",
                    textfont=dict(size=10, color="#ffffff"),
                    customdata=rdf[["talent", "achievement_focus"]],
                    hovertemplate=(
                        "%{customdata[0]}<br>"
                        "Week of %{x|%b %-d, %Y}<br>"
                        f"{relation}<br>"
                        "Focus: %{customdata[1]}<extra></extra>"
                    ),
                ))
            client_relation_fig.update_layout(
                title=dict(text="Work Continuity by Talent and Week", font=dict(size=13)),
                legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="center", x=0.5, font=dict(size=10)),
            )
            client_relation_fig.update_xaxes(
                title=None,
                tickformat="%b %-d",
                tickvals=client_story.sort_values("week_start")["week_start"].drop_duplicates().tolist(),
                tickangle=0,
                tickfont=dict(size=10),
                automargin=True,
            )
            client_relation_fig.update_yaxes(title=None, automargin=True)
            _chart_layout(client_relation_fig, height=max(300, 105 + len(client_talent_order) * 36), showlegend=True)
            client_relation_fig.update_layout(margin=dict(l=8, r=8, t=48, b=86))

            group_counts = (
                client_story[["talent", "talent_group"]]
                .drop_duplicates(subset=["talent"])
                .assign(Badge=lambda d: d["talent_group"].map(_group_badge))
                ["Badge"]
                .value_counts()
                .reindex(["A", "E", "I"], fill_value=0)
            )
            level_html = f"""
            <div style="display:flex; justify-content:flex-end; margin: 0;">
              <div style="max-width: 360px;">
                <div style="font-weight: 700; color: #0f172a; margin-bottom: .35rem; font-size:.9rem;">Talent Classification</div>
                <div style="display: flex; align-items: center; gap: .35rem; flex-wrap: nowrap;">
                  <div style="border:1px solid #cbd5e1; border-radius:7px; padding:.35rem .5rem; min-width:56px; text-align:center;">
                    <div style="font-size:1rem; font-weight:800; line-height:1;">A</div>
                    <div style="font-size:.72rem; color:#475569;">{int(group_counts.get("A", 0))}</div>
                  </div>
                  <div style="font-weight:800; color:#64748b; font-size:.85rem;">→</div>
                  <div style="border:1px solid #cbd5e1; border-radius:7px; padding:.35rem .5rem; min-width:56px; text-align:center;">
                    <div style="font-size:1rem; font-weight:800; line-height:1;">E</div>
                    <div style="font-size:.72rem; color:#475569;">{int(group_counts.get("E", 0))}</div>
                  </div>
                  <div style="font-weight:800; color:#64748b; font-size:.85rem;">→</div>
                  <div style="border:1px solid #cbd5e1; border-radius:7px; padding:.35rem .5rem; min-width:56px; text-align:center;">
                    <div style="font-size:1rem; font-weight:800; line-height:1;">I</div>
                    <div style="font-size:.72rem; color:#475569;">{int(group_counts.get("I", 0))}</div>
                  </div>
                </div>
                <div style="margin-top:.25rem; color:#475569; font-size:.72rem;">A → E → I progression</div>
              </div>  
            </div>
            """

            header_col1, header_col2 = st.columns([1.15, 1])
            with header_col1:
                st.markdown("##### Weekly Achievement Story")
                if pd.notna(client_start) and pd.notna(client_end):
                    st.markdown(
                        f"**Reporting period:** {client_start.strftime('%b %-d, %Y')} to "
                        f"{client_end.strftime('%b %-d, %Y')} ({client_week_count} submitted week(s))"
                    )
                st.caption("Each cell shows Task Complexity plus continuity: S = Same, R = Related, D = Different, F = First visible update.")
            with header_col2:
                st.markdown(level_html, unsafe_allow_html=True)

            client_ach_col1, client_ach_col2 = st.columns([1.15, 1])
            with client_ach_col1:
                st.plotly_chart(client_timeline_fig, use_container_width=True, key=f"achievement_workmap_{client}")
            with client_ach_col2:
                st.plotly_chart(client_relation_fig, use_container_width=True, key=f"achievement_relation_{client}")


# --- Navigation ---
talent_profiles_page = st.Page(page_talent_profiles, title="Talents", url_path="talent-profiles", default=True)
client_portfolio_page = st.Page(page_client_portfolio, title="Clients", url_path="clients")
weekly_status_page = st.Page(page_weekly_status, title="Weekly", url_path="weekly")
evidence_review_page = st.Page(page_evidence_review, title="Evidence Review", url_path="evidence-review")
data_source_page = st.Page(page_data_source, title="Data", url_path="data")

pg = st.navigation(
    [talent_profiles_page, client_portfolio_page, weekly_status_page, evidence_review_page, data_source_page],
    position="top",
)

# --- Deep link support: ?selected_talent=<email> jumps straight to that talent's profile ---
if "selected_talent" in st.query_params:
    _tgt_talent = st.query_params["selected_talent"]
    st.query_params.clear()
    if _tgt_talent in people:
        st.session_state.selected_talent = _tgt_talent
        st.switch_page(talent_profiles_page)

with st.container(key="custom_top_navbar"):
    nav_talents, nav_clients, nav_weekly, nav_evidence, nav_data, nav_refresh = st.columns([1, 1, 1, 1.45, 1, 0.9])
    with nav_talents:
        st.page_link(talent_profiles_page, label="Talents")
    with nav_clients:
        st.page_link(client_portfolio_page, label="Clients")
    with nav_weekly:
        st.page_link(weekly_status_page, label="Weekly")
    with nav_evidence:
        st.page_link(evidence_review_page, label="Evidence Review")
    with nav_data:
        st.page_link(data_source_page, label="Data")
    with nav_refresh:
        if st.button("Refresh", key="btn_refresh", use_container_width=True, help="Clear cache and reload data"):
            st.cache_data.clear()
            st.rerun()

pg.run()
