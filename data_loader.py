"""Load weekly Telegram check-in data from demo, published CSV, or Google Sheets API."""

from __future__ import annotations

import csv
import io
import ssl
import urllib.request
from dataclasses import dataclass

import certifi
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

# Map Google Form / Telegram export headers → internal column names
COLUMN_ALIASES: dict[str, str] = {
    "Timestamp": "timestamp",
    "Email address": "email",
    "What were your key achievements of the week?": "key_achievements",
    "Key achievements": "key_achievements",
    "Number of tickets actually completed QA or Done?": "tickets_completed",
    "Tickets completed": "tickets_completed",
    "Expected number of tickets to get completed": "tickets_expected",
    "Expected tickets": "tickets_expected",
    "% of tickets that passed QA on first attempt": "qa_first_pass_pct",
    "% passed QA first attempt": "qa_first_pass_pct",
    "What were your challenges of the week?": "challenges",
    "Challenges of the week": "challenges",
    "Have you met all the expectations of your employer for this week?": "met_expectations",
    "Overall rating of your performance this week?": "overall_rating",
    "Overall rating": "overall_rating",
    "Write here any other things you want to highlight (optional)": "other_highlights",
    "Upload any image or document you want us to see (optional)": "upload",
}

# Fallback when exact header text differs slightly (BOM, spacing, copy/paste)
_SUBSTRING_ALIASES: tuple[tuple[str, str], ...] = (
    ("timestamp", "timestamp"),
    ("email address", "email"),
    ("key achievements of the week", "key_achievements"),
    ("key achievements", "key_achievements"),
    ("tickets actually completed", "tickets_completed"),
    ("expected number of tickets", "tickets_expected"),
    ("passed qa on first attempt", "qa_first_pass_pct"),
    ("challenges of the week", "challenges"),
    ("met all the expectations", "met_expectations"),
    ("overall rating of your performance", "overall_rating"),
    ("overall rating", "overall_rating"),
    ("other things you want to highlight", "other_highlights"),
    ("upload any image or document", "upload"),
)

_ALIAS_BY_LOWER = {k.lower(): v for k, v in COLUMN_ALIASES.items()}

_TEXT_HEADER_KEYWORDS = (
    "achievement",
    "challenge",
    "highlight",
    "upload",
    "other",
    "comment",
    "feedback",
)


@dataclass
class CsvParseInfo:
    """Metadata from robust CSV parsing (for UI warnings)."""
    total_rows: int = 0
    repaired_rows: int = 0
    skipped_rows: int = 0
    parser_used: str = ""


def get_secret(key: str, default: str = "") -> str:
    """Read a secret without failing when secrets.toml is missing."""
    try:
        return st.secrets.get(key, default)
    except (StreamlitSecretNotFoundError, KeyError, FileNotFoundError):
        return default


def _clean_header(name: str) -> str:
    """Strip BOM, collapse whitespace, normalize for matching."""
    cleaned = str(name).replace("\ufeff", "").strip()
    return " ".join(cleaned.split())


def _canonical_name(header: str) -> str | None:
    """Map a sheet header to an internal column name."""
    if header in COLUMN_ALIASES:
        return COLUMN_ALIASES[header]
    lower = header.lower()
    if lower in _ALIAS_BY_LOWER:
        return _ALIAS_BY_LOWER[lower]
    for needle, canonical in _SUBSTRING_ALIASES:
        if needle in lower:
            return canonical
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename: dict[str, str] = {}
    for col in df.columns:
        cleaned = _clean_header(col)
        canonical = _canonical_name(cleaned)
        if canonical:
            rename[col] = canonical
    df = df.rename(columns=rename)
    # Drop duplicate internal names (keep first) after rename collisions
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()]
    return df


def _detect_delimiter(text: str) -> str:
    """Google exports are usually CSV; pasted copies may be tab-separated."""
    first_line = text.splitlines()[0] if text else ""
    if first_line.count("\t") > first_line.count(","):
        return "\t"
    return ","


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], dayfirst=True, errors="coerce")
    for col in ("tickets_completed", "tickets_expected", "overall_rating"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "qa_first_pass_pct" in df.columns:
        df["qa_first_pass_pct"] = (
            df["qa_first_pass_pct"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        df["qa_first_pass_pct"] = pd.to_numeric(df["qa_first_pass_pct"], errors="coerce")
    for col in ("key_achievements", "challenges", "other_highlights", "email"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    if "timestamp" in df.columns:
        df["week"] = df["timestamp"].dt.to_period("W").astype(str)
    return df


def validate_sheet_dataframe(df: pd.DataFrame) -> None:
    """Reject HTML pages or broken exports mistaken for CSV."""
    if df.empty:
        raise ValueError("Sheet is empty.")
    first_col = str(df.columns[0]).lower()
    if "<!doctype" in first_col or "<html" in first_col:
        raise ValueError(
            "This URL returned a web page, not CSV data. "
            "In Google Sheets use File → Share → Publish to web → "
            "Comma-separated values (.csv). The link must end with "
            "`/pub?output=csv`, not `pubhtml` or `/edit`."
        )
    if "email" not in df.columns:
        raise ValueError(
            "No email column found after loading. "
            f"Columns detected: {list(df.columns)[:6]}…"
        )


def _fetch_csv_text(url: str) -> str:
    """Download published sheet CSV with certifi-backed SSL."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    request = urllib.request.Request(url, headers={"User-Agent": "TenaciousGrowthDashboard/1.0"})
    with urllib.request.urlopen(request, context=ctx, timeout=60) as response:
        text = response.read().decode("utf-8-sig", errors="replace")
    return text.lstrip("\ufeff")


def _text_column_indices(header: list[str]) -> set[int]:
    indices = {
        i
        for i, name in enumerate(header)
        if any(kw in name.lower() for kw in _TEXT_HEADER_KEYWORDS)
    }
    if indices:
        return indices
    # Form exports: timestamp + email, then free-text blocks
    return set(range(2, min(len(header), 9)))


def _repair_csv_row(row: list[str], n_cols: int, text_indices: set[int]) -> list[str]:
    """Merge extra comma-split fields back into free-text columns."""
    if len(row) == n_cols:
        return row
    if len(row) < n_cols:
        return row + [""] * (n_cols - len(row))

    out: list[str] = []
    i = 0
    for col_idx in range(n_cols):
        fields_left = len(row) - i
        cols_left = n_cols - col_idx
        merge_count = fields_left - cols_left + 1

        if merge_count > 1 and (col_idx in text_indices or cols_left == 1):
            out.append(",".join(row[i : i + merge_count]))
            i += merge_count
        else:
            out.append(row[i] if i < len(row) else "")
            i += 1
    return out[:n_cols]


def _parse_csv_with_row_repair(text: str, sep: str = ",") -> tuple[pd.DataFrame, CsvParseInfo]:
    reader = csv.reader(io.StringIO(text), delimiter=sep)
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    info = CsvParseInfo(parser_used=f"csv_row_repair({sep!r})")

    if not rows:
        return pd.DataFrame(), info

    header = [_clean_header(c) for c in rows[0]]
    n_cols = len(header)
    text_indices = _text_column_indices(header)
    fixed: list[list[str]] = []

    for row in rows[1:]:
        repaired = _repair_csv_row(row, n_cols, text_indices)
        if len(repaired) == n_cols:
            if len(row) != n_cols:
                info.repaired_rows += 1
            fixed.append(repaired)
        else:
            info.skipped_rows += 1

    info.total_rows = len(fixed)
    return pd.DataFrame(fixed, columns=header), info


def _parse_csv_text(text: str) -> tuple[pd.DataFrame, CsvParseInfo]:
    """Try strict parsers first, then row-repair for messy Google exports."""
    sep = _detect_delimiter(text)
    attempts: list[tuple[str, dict]] = [
        ("pandas_c", {"engine": "c", "sep": sep}),
        (
            "pandas_python",
            {
                "engine": "python",
                "sep": sep,
                "quoting": csv.QUOTE_MINIMAL,
                "on_bad_lines": "error",
            },
        ),
        (
            "pandas_python_skip",
            {
                "engine": "python",
                "sep": sep,
                "quoting": csv.QUOTE_MINIMAL,
                "on_bad_lines": "skip",
            },
        ),
    ]

    for name, kwargs in attempts:
        buf = io.StringIO(text)
        try:
            df = pd.read_csv(buf, **kwargs)
            skipped = max(0, text.count("\n") - len(df) - 1)  # rough; skip path only
            info = CsvParseInfo(
                total_rows=len(df),
                parser_used=f"{name}({sep!r})",
                skipped_rows=skipped if name == "pandas_python_skip" else 0,
            )
            return df, info
        except (pd.errors.ParserError, csv.Error):
            continue

    df, info = _parse_csv_with_row_repair(text, sep=sep)
    return df, info


@st.cache_data(ttl=300, show_spinner="Loading sheet data…")
def load_from_csv_url(url: str) -> tuple[pd.DataFrame, CsvParseInfo]:
    text = _fetch_csv_text(url)
    if text.lstrip().lower().startswith("<!doctype") or "<html" in text[:500].lower():
        raise ValueError(
            "This URL returned HTML, not CSV. Use a published CSV link ending in "
            "`/pub?output=csv` (File → Share → Publish to web → CSV)."
        )
    df, info = _parse_csv_text(text)
    df = _coerce_types(_normalize_columns(df))
    validate_sheet_dataframe(df)
    return df, info


@st.cache_data(ttl=300, show_spinner="Loading Google Sheet…")
def load_from_gspread(spreadsheet_id: str, worksheet_name: str | None = None) -> pd.DataFrame:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        raise ImportError(
            "Install gspread and google-auth: pip install gspread google-auth"
        ) from e

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    try:
        sa = st.secrets["gcp_service_account"]
    except (StreamlitSecretNotFoundError, KeyError) as e:
        raise ValueError(
            "Add [gcp_service_account] to .streamlit/secrets.toml (see secrets.toml.example)"
        ) from e
    creds = Credentials.from_service_account_info(dict(sa), scopes=scopes)

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    return _coerce_types(_normalize_columns(df))


def load_sheet(csv_url: str | None = None) -> tuple[pd.DataFrame, CsvParseInfo]:
    """Load the Telegram weekly check-in Google Sheet (published CSV)."""
    url = (csv_url or "").strip() or get_secret("sheet_csv_url", "").strip()
    if not url:
        raise ValueError(
            "Set `sheet_csv_url` in `.streamlit/secrets.toml` (no `#` at the start of the line). "
            "The link must include `output=csv` from Publish to web → CSV."
        )
    if "pubhtml" in url or "output=csv" not in url:
        raise ValueError(
            "URL must be a published **CSV** link (contains `output=csv`). "
            "Republish via File → Share → Publish to web → Comma-separated values (.csv)."
        )
    return load_from_csv_url(url)
