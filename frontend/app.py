import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st
from utils.api_client import ApiClient, cached_biomarker_summary, cached_reports
from utils.theme import (
    apply_theme,
    get_colors,
    kpi_tile,
    render_sidebar_profile,
)

st.set_page_config(
    page_title="Medical Lab Insights",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
COLORS = get_colors()

# ── Session defaults ──────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

client = ApiClient(token=st.session_state.token)

# ── Logged-in view ────────────────────────────────────────────────────────
if st.session_state.token:
    render_sidebar_profile()

    user = st.session_state.get("user", {})
    name = user.get("full_name") or user.get("email", "").split("@")[0]

    st.markdown(
        f"""
        <div style="margin-bottom:8px;">
            <span style="font-size:1.8rem;font-weight:800;color:{COLORS['text']};">
                Welcome back, {name}
            </span>
            <span style="font-size:1.8rem;">👋</span>
        </div>
        <p style="color:{COLORS['text_muted']};margin-top:0;">
            Here&rsquo;s a quick snapshot of your lab data.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Quick stats (cached)
    token = st.session_state.token
    r_ok, reps = cached_reports(token)
    s_ok, rows = cached_biomarker_summary(token)

    total_reports = 0
    latest_upload = "—"
    if r_ok:
        total_reports = len(reps)
        if reps:
            latest_upload = reps[0].get("report_date") or reps[0].get("created_at", "—")

    total_biomarkers = 0
    flagged = 0
    if s_ok:
        total_biomarkers = len(rows)
        flagged = sum(1 for r in rows if r.get("flag"))

    cols = st.columns(4)
    tiles = [
        ("Reports Uploaded", total_reports, COLORS["primary"]),
        ("Biomarkers Tracked", total_biomarkers, COLORS["info"]),
        ("Flagged Results", flagged, COLORS["danger"] if flagged else COLORS["success"]),
        ("Latest Report", latest_upload, COLORS["text"]),
    ]
    for col, (label, value, color) in zip(cols, tiles):
        col.markdown(kpi_tile(label, value, color), unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Navigation cards
    nav_items = [
        ("📤", "Upload Report", "Parse a new lab PDF and store results.", "1_upload"),
        ("📊", "Dashboard", "Explore biomarkers by category with rich visuals.", "2_dashboard"),
        ("📈", "Trends", "See how your biomarkers are changing over time.", "3_trends"),
        ("📋", "Report Detail", "View the full breakdown of any uploaded report.", "4_report_detail"),
        ("🩺", "Health Overview", "Your overall health score and actionable insights.", "5_health_overview"),
        ("🔀", "Compare Reports", "Side-by-side comparison of two lab reports.", "6_compare"),
    ]

    nav_cols = st.columns(len(nav_items))
    for col, (icon, title, desc, _page) in zip(nav_cols, nav_items):
        col.markdown(
            f"""
            <div class="nav-card">
                <div class="nav-icon">{icon}</div>
                <div class="nav-title">{title}</div>
                <div class="nav-desc">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Auth view ─────────────────────────────────────────────────────────────
else:
    _spacer_l, center, _spacer_r = st.columns([1, 2, 1])
    with center:
        st.markdown(
            f"""
            <div style="text-align:center;margin-top:40px;margin-bottom:8px;">
                <span style="font-size:3rem;">🧬</span>
            </div>
            <h1 style="text-align:center;color:{COLORS['text']};margin-bottom:4px;">
                Medical Lab Insights
            </h1>
            <p style="text-align:center;color:{COLORS['text_muted']};margin-bottom:32px;">
                Upload, track, and understand your lab results over time.
            </p>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                pwd = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
            if submitted:
                if not email or not pwd:
                    st.error("Please enter both email and password.")
                else:
                    res = client.login(email, pwd)
                    if res.ok:
                        data = res.json()
                        st.session_state.token = data["token"]
                        st.session_state.user = data["user"]
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

        with tab_register:
            with st.form("register_form"):
                name = st.text_input("Full name", placeholder="Jane Doe")
                email_r = st.text_input("Email", placeholder="you@example.com", key="reg_em")
                pwd_r = st.text_input("Password", type="password", placeholder="Min 6 characters", key="reg_pw")
                submitted_r = st.form_submit_button("Create account", use_container_width=True, type="primary")
            if submitted_r:
                if not email_r or not pwd_r:
                    st.error("Email and password are required.")
                elif len(pwd_r) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    res = client.register(email=email_r, password=pwd_r, full_name=name)
                    if res.ok:
                        data = res.json()
                        st.session_state.token = data["token"]
                        st.session_state.user = data["user"]
                        st.rerun()
                    else:
                        try:
                            detail = res.json().get("error", {}).get("details", {}).get("reason", res.text)
                        except Exception:
                            detail = res.text
                        st.error(f"Registration failed: {detail}")
