import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import plotly.graph_objects as go
import streamlit as st

from utils.api_client import ApiClient, cached_reports
from utils.theme import (
    apply_theme,
    auth_guard,
    get_colors,
    kpi_tile,
    pill_tag,
    plotly_layout_defaults,
    render_sidebar_profile,
    section_title,
)

st.set_page_config(page_title="Upload Report", page_icon="📤", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

client = ApiClient(token=st.session_state.token)

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">📤 Upload Lab Report</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        Upload a PDF lab report to parse, classify biomarkers, and track trends.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Upload area ───────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
file = st.file_uploader(
    "Drag and drop your lab report PDF here",
    type=["pdf"],
    help="Supported: single-file PDF lab reports",
)

if file:
    size_kb = len(file.getvalue()) / 1024
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;margin:8px 0 4px 0;">
            <span style="font-size:1.5rem;">📄</span>
            <div>
                <div style="font-weight:600;color:{COLORS['text']};">{file.name}</div>
                <div style="color:{COLORS['text_muted']};font-size:0.82rem;">{size_kb:.1f} KB</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

submit = st.button("Parse and Save", disabled=file is None, use_container_width=True, type="primary")
st.markdown("</div>", unsafe_allow_html=True)

if submit and file:
    progress = st.progress(0, text="Uploading and parsing report...")
    progress.progress(15, text="Sending PDF to parser...")
    res = client.upload_report((file.name, file, "application/pdf"))
    progress.progress(90, text="Processing results...")

    if res.ok:
        progress.progress(100, text="Done!")
        data = res.json()
        total = data.get("tests", 0)
        mapped = data.get("mapped_tests", 0)
        unmapped_count = data.get("unmapped_tests_count", 0)
        unmapped_names = data.get("unmapped_tests_preview", [])

        st.success(f"Report **{file.name}** processed successfully!")

        # ── Result KPIs ───────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        c1.markdown(kpi_tile("Total Tests", total, COLORS["primary"]), unsafe_allow_html=True)
        c2.markdown(kpi_tile("Mapped", mapped, COLORS["success"]), unsafe_allow_html=True)
        c3.markdown(kpi_tile("Unmapped", unmapped_count, COLORS["warning"] if unmapped_count else COLORS["success"]), unsafe_allow_html=True)

        # ── Donut chart ───────────────────────────────────────────────
        if total > 0:
            fig = go.Figure(
                go.Pie(
                    labels=["Mapped", "Unmapped"],
                    values=[mapped, unmapped_count],
                    hole=0.55,
                    marker=dict(colors=[COLORS["success"], COLORS["warning"]]),
                    textinfo="label+percent",
                    textfont=dict(size=13),
                )
            )
            fig.update_layout(
                **plotly_layout_defaults("Classification Breakdown", height=300),
                showlegend=False,
            )
            fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # ── Unmapped pills ────────────────────────────────────────────
        if unmapped_names:
            st.markdown(
                '<p style="color:{}; font-size:0.85rem; margin-bottom:4px;">⚠️ Unmapped tests (first {}):</p>'.format(
                    COLORS["text_muted"], len(unmapped_names)
                ),
                unsafe_allow_html=True,
            )
            pills_html = " ".join(pill_tag(n, warning=True) for n in unmapped_names)
            st.markdown(pills_html, unsafe_allow_html=True)

        # Bust the reports cache so the new report appears
        cached_reports.clear()
    else:
        progress.empty()
        try:
            detail = res.json().get("error", {}).get("details", {}).get("reason", res.text)
        except Exception:
            detail = res.text
        st.error(f"Upload failed: {detail}")

# ── Upload history ────────────────────────────────────────────────────────
section_title("Upload History")
ok, reps = cached_reports(st.session_state.token)
if ok:
    if reps:
        for r in reps[:10]:
            date_str = r.get("report_date") or "No date"
            lab = r.get("lab_name") or "Unknown lab"
            patient = r.get("patient_name", "")
            st.markdown(
                f"""
                <div class="info-card" style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div class="info-value">{lab}</div>
                        <div class="info-label">{patient} &middot; {date_str}</div>
                    </div>
                    <div style="color:{COLORS['text_muted']};font-size:0.82rem;">{r.get('doc_id','')[:8]}…</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No reports uploaded yet. Upload your first report above!")
else:
    st.caption("Could not load report history.")
