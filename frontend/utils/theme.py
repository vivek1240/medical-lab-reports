"""
Shared theme, CSS injection, color palette, and UI helper functions
for the Medical Lab Insights Streamlit frontend.
"""

from __future__ import annotations

import re
import streamlit as st

# ---------------------------------------------------------------------------
# Color palettes (light + dark)
# ---------------------------------------------------------------------------
COLORS_LIGHT: dict[str, str] = {
    "primary": "#0D9488",       # teal-600
    "primary_light": "#5EEAD4", # teal-300
    "primary_dark": "#115E59",  # teal-800
    "accent": "#F97316",        # orange-500
    "danger": "#EF4444",        # red-500
    "danger_light": "#FEE2E2",  # red-100
    "warning": "#F59E0B",       # amber-500
    "warning_light": "#FEF3C7", # amber-100
    "success": "#10B981",       # emerald-500
    "success_light": "#D1FAE5", # emerald-100
    "info": "#3B82F6",          # blue-500
    "info_light": "#DBEAFE",    # blue-100
    "text": "#1E293B",          # slate-800
    "text_secondary": "#475569", # slate-600
    "text_muted": "#475569",    # slate-600
    "bg_card": "#FFFFFF",
    "bg_page": "#F8FAFC",       # slate-50
    "border": "#E2E8F0",        # slate-200
    "up": "#EF4444",
    "down": "#3B82F6",
    "stable": "#10B981",
}

COLORS_DARK: dict[str, str] = {
    "primary": "#14B8A6",       # teal-400
    "primary_light": "#5EEAD4", # teal-300
    "primary_dark": "#0D9488",  # teal-600
    "accent": "#FB923C",        # orange-400
    "danger": "#F87171",        # red-400
    "danger_light": "#450A0A",  # red-950
    "warning": "#FBBF24",       # amber-400
    "warning_light": "#451A03", # amber-950
    "success": "#34D399",       # emerald-400
    "success_light": "#022C22", # emerald-950
    "info": "#60A5FA",          # blue-400
    "info_light": "#172554",    # blue-950
    "text": "#F1F5F9",          # slate-100
    "text_secondary": "#CBD5E1", # slate-300
    "text_muted": "#94A3B8",    # slate-400
    "bg_card": "#1E293B",       # slate-800
    "bg_page": "#0F172A",       # slate-900
    "border": "#334155",        # slate-700
    "up": "#F87171",
    "down": "#60A5FA",
    "stable": "#34D399",
}

# Module-level default (light) – kept for backward compat on first import.
COLORS = COLORS_LIGHT


def get_colors() -> dict[str, str]:
    """Return the active palette based on ``st.session_state.dark_mode``."""
    if st.session_state.get("dark_mode", False):
        return COLORS_DARK
    return COLORS_LIGHT


# ---------------------------------------------------------------------------
# Plotly helpers (palette-aware)
# ---------------------------------------------------------------------------
PLOTLY_COLORS = [
    COLORS_LIGHT["primary"], COLORS_LIGHT["accent"], COLORS_LIGHT["info"],
    COLORS_LIGHT["success"], COLORS_LIGHT["danger"], COLORS_LIGHT["warning"],
    "#8B5CF6", "#EC4899", "#14B8A6", "#F43F5E",
]


def _plotly_template() -> str:
    if st.session_state.get("dark_mode", False):
        return "plotly_dark"
    return "plotly_white"


def plotly_layout_defaults(title: str = "", height: int = 400) -> dict:
    """Return a dict of common Plotly layout kwargs for consistent styling."""
    c = get_colors()
    _axis_common = dict(
        tickfont=dict(size=12, color=c["text"]),
        title=dict(font=dict(size=13, color=c["text"])),
        linecolor=c["border"],
        gridcolor=c["border"],
    )
    bg = "rgba(0,0,0,0)" if not st.session_state.get("dark_mode") else c["bg_card"]
    return dict(
        title=dict(text=title, font=dict(size=16, color=c["text"])),
        template=_plotly_template(),
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="Inter, system-ui, sans-serif", size=13, color=c["text"]),
        plot_bgcolor=bg,
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(**_axis_common),
        yaxis=dict(**_axis_common),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        coloraxis=dict(
            colorbar=dict(
                tickfont=dict(size=11, color=c["text"]),
                title=dict(font=dict(size=12, color=c["text"])),
            )
        ),
    )


# Keep module-level constant for legacy imports (still light default)
PLOTLY_TEMPLATE = "plotly_white"


# ---------------------------------------------------------------------------
# CSS injection (built dynamically for active palette)
# ---------------------------------------------------------------------------
_CSS_TEMPLATE = """
<style>
/* ---------- Page background & base text ---------- */
[data-testid="stAppViewContainer"] {
    background-color: %(bg_page)s;
}
/* Dark text only in MAIN content area, NOT the sidebar */
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] p,
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] span,
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] td,
[data-testid="stAppViewContainer"] > section[data-testid="stMain"] li {
    color: %(text)s;
}
[data-testid="stMain"] [data-testid="stExpander"] summary span {
    color: %(text)s !important;
}

/* ---------- Metric cards ---------- */
div[data-testid="stMetric"] {
    background: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
div[data-testid="stMetric"] label {
    color: %(text_muted)s !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: %(text)s !important;
}

/* ---------- Card container ---------- */
.card {
    background: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.card-header {
    font-weight: 700;
    font-size: 1.05rem;
    color: %(text)s;
    margin-bottom: 12px;
}
.card-muted {
    color: %(text_muted)s;
    font-size: 0.85rem;
}

/* ---------- Flag badges ---------- */
.flag-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.flag-high  { background: %(danger_light)s; color: %(danger)s; }
.flag-low   { background: %(info_light)s;   color: %(info)s; }
.flag-normal { background: %(success_light)s; color: %(success)s; }

/* ---------- Pill tags ---------- */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 2px 4px 2px 0;
    border: 1px solid %(border)s;
    background: %(bg_card)s;
    color: %(text_muted)s;
}
.pill-warning {
    background: %(warning_light)s;
    color: %(warning)s;
    border-color: %(warning)s;
}

/* ---------- KPI tile ---------- */
.kpi-tile {
    background: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
}
.kpi-label {
    font-size: 0.82rem;
    color: %(text_muted)s;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 6px;
}

/* ---------- Info card ---------- */
.info-card {
    background: %(bg_card)s;
    border: 1px solid %(border)s;
    border-left: 4px solid %(primary)s;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    color: %(text)s;
    font-size: 0.92rem;
    line-height: 1.5;
}
.info-card span { color: %(text)s; }
.info-card strong, .info-card b { color: %(text)s; font-weight: 700; }
.info-label { color: %(text_secondary)s; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
.info-value { color: %(text)s; font-size: 1rem; font-weight: 600; }

/* ---------- Nav card ---------- */
.nav-card {
    background: %(bg_card)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    transition: box-shadow 0.2s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.nav-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.nav-icon { font-size: 2rem; margin-bottom: 8px; }
.nav-title { font-weight: 700; font-size: 1rem; color: %(text)s; }
.nav-desc { color: %(text_muted)s; font-size: 0.82rem; margin-top: 4px; }

/* ---------- Direction arrows ---------- */
.dir-up    { color: %(danger)s;  font-weight: 700; }
.dir-down  { color: %(info)s;    font-weight: 700; }
.dir-stable { color: %(success)s; font-weight: 700; }

/* ---------- Section title ---------- */
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: %(text)s;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid %(primary)s;
    display: inline-block;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background-color: %(bg_card)s !important;
}
[data-testid="stSidebar"] * {
    color: %(text)s !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    font-size: 0.88rem;
    color: %(text)s !important;
}
/* Sidebar nav links */
[data-testid="stSidebarNav"] a span {
    color: %(text)s !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: %(primary)s !important;
    font-weight: 700;
}
/* Sidebar buttons stay readable */
[data-testid="stSidebar"] button {
    color: %(text)s !important;
    border-color: %(border)s !important;
}

/* ---------- Table tweaks ---------- */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ---------- Global table readability (main content only) ---------- */
[data-testid="stMain"] table td { color: %(text)s; }
[data-testid="stMain"] table th { color: %(text_secondary)s !important; }

/* ---------- Tabs readability ---------- */
button[data-baseweb="tab"] {
    color: %(text_muted)s !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: %(primary)s !important;
}

/* ---------- Text inputs ---------- */
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
input[type="text"],
input[type="password"],
input[type="email"],
textarea {
    color: %(text)s !important;
    background-color: %(bg_card)s !important;
    border-color: %(border)s !important;
}
/* Placeholder text */
input::placeholder,
textarea::placeholder {
    color: %(text_muted)s !important;
    opacity: 0.7 !important;
}
/* Form labels */
[data-testid="stTextInput"] label,
[data-testid="stDateInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stFileUploader"] label,
[data-testid="stSlider"] label,
[data-testid="stMultiSelect"] label {
    color: %(text)s !important;
}
/* Selectbox / multiselect dropdown text */
[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: %(text)s !important;
}
/* Password visibility toggle */
[data-testid="stTextInput"] button svg {
    fill: %(text_muted)s !important;
}
</style>
"""


def apply_theme() -> None:
    """Inject global CSS into the page. Call once at the top of every page."""
    # Ensure dark_mode key exists
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    colors = get_colors()
    st.markdown(_CSS_TEMPLATE % colors, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------
def auth_guard() -> None:
    """Stop page execution with a friendly message if not logged in."""
    if "token" not in st.session_state or not st.session_state.token:
        st.warning("Please log in from the **Home** page to continue.")
        st.stop()


# ---------------------------------------------------------------------------
# Sidebar profile / logout / dark-mode toggle
# ---------------------------------------------------------------------------
def render_sidebar_profile() -> None:
    """Render user avatar, email, logout button, and dark-mode toggle."""
    if not st.session_state.get("token"):
        return
    user = st.session_state.get("user", {})
    email = user.get("email", "")
    name = user.get("full_name") or email.split("@")[0]
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
    c = get_colors()

    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center; padding: 16px 0 8px 0;">
                <div style="width:56px;height:56px;border-radius:50%;background:{c['primary']};
                    color:white;font-size:1.3rem;font-weight:700;display:inline-flex;
                    align-items:center;justify-content:center;margin-bottom:6px;">
                    {initials}
                </div>
                <div style="font-weight:600;color:{c['text']};font-size:0.95rem;">{name}</div>
                <div style="color:{c['text_muted']};font-size:0.8rem;">{email}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # Dark-mode toggle
        dark = st.toggle(
            "🌙 Dark mode",
            value=st.session_state.get("dark_mode", False),
            key="dark_mode_toggle",
        )
        if dark != st.session_state.get("dark_mode", False):
            st.session_state.dark_mode = dark
            st.rerun()

        if st.button("Logout", use_container_width=True, type="secondary"):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
        st.divider()


# ---------------------------------------------------------------------------
# Reusable HTML helpers
# ---------------------------------------------------------------------------
def flag_badge(flag: str | None) -> str:
    """Return an HTML span styled as a flag badge."""
    if not flag:
        return '<span class="flag-badge flag-normal">NORMAL</span>'
    key = flag.strip().upper()
    if key in ("H", "HIGH", "HH"):
        return f'<span class="flag-badge flag-high">{key}</span>'
    if key in ("L", "LOW", "LL"):
        return f'<span class="flag-badge flag-low">{key}</span>'
    return f'<span class="flag-badge flag-normal">{key}</span>'


def direction_arrow(direction: str) -> str:
    """Return an HTML arrow element for trend direction."""
    if direction == "up":
        return '<span class="dir-up">&#9650; Up</span>'
    if direction == "down":
        return '<span class="dir-down">&#9660; Down</span>'
    return '<span class="dir-stable">&#9654; Stable</span>'


def kpi_tile(label: str, value: str | int | float, color: str) -> str:
    """Return HTML for a single KPI tile."""
    return (
        f'<div class="kpi-tile">'
        f'  <div class="kpi-value" style="color:{color};">{value}</div>'
        f'  <div class="kpi-label">{label}</div>'
        f'</div>'
    )


def section_title(text: str) -> None:
    """Render a styled section heading."""
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def pill_tag(text: str, warning: bool = False) -> str:
    """Return HTML for a small pill tag."""
    cls = "pill pill-warning" if warning else "pill"
    return f'<span class="{cls}">{text}</span>'


# ---------------------------------------------------------------------------
# Reference range parsing
# ---------------------------------------------------------------------------
_RANGE_RE = re.compile(
    r"(?P<low>[\d.]+)\s*[-–]\s*(?P<high>[\d.]+)"
)


def parse_reference_range(range_str: str | None) -> tuple[float | None, float | None]:
    """
    Extract (low, high) floats from a reference range string like '3.5 - 5.0'.
    Returns (None, None) if unparseable.
    """
    if not range_str:
        return None, None
    m = _RANGE_RE.search(range_str)
    if not m:
        return None, None
    try:
        return float(m.group("low")), float(m.group("high"))
    except (ValueError, TypeError):
        return None, None


def safe_float(val: str | None) -> float | None:
    """Parse a value string to float, returning None on failure."""
    if val is None:
        return None
    cleaned = "".join(ch for ch in val if ch.isdigit() or ch in {".", "-"})
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None
