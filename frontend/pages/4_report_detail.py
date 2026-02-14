import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import io
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api_client import cached_report_detail, cached_reports
from utils.theme import (
    apply_theme,
    auth_guard,
    flag_badge,
    get_colors,
    kpi_tile,
    parse_reference_range,
    plotly_layout_defaults,
    render_sidebar_profile,
    safe_float,
    section_title,
)

st.set_page_config(page_title="Report Detail", page_icon="📋", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

token = st.session_state.token

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">📋 Report Explorer</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        View the full breakdown of any uploaded lab report.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Report selector (cached) ─────────────────────────────────────────────
r_ok, reports = cached_reports(token)
if not r_ok:
    st.error("Failed to load reports.")
    st.stop()
if not reports:
    st.info("No reports available. Upload a report first.")
    st.stop()

options = {
    f"{r.get('report_date') or 'No date'} — {r.get('lab_name') or 'Unknown lab'} — {r.get('patient_name', '')}": r["doc_id"]
    for r in reports
}
choice = st.selectbox("Select report", options=list(options.keys()))
doc_id = options[choice]

d_ok, data = cached_report_detail(token, doc_id)
if not d_ok:
    st.error("Failed to load report detail.")
    st.stop()

patient = data.get("patient_info", {})
tests = data.get("test_results", [])

# ── Patient info card ─────────────────────────────────────────────────────
section_title("Patient & Report Information")

info_items = [
    ("Patient Name", patient.get("name", "—")),
    ("Date of Birth", patient.get("date_of_birth") or "—"),
    ("Gender", patient.get("gender") or "—"),
    ("Patient ID", patient.get("patient_id") or "—"),
    ("Lab Name", data.get("lab_name") or "—"),
    ("Physician", data.get("physician_name") or "—"),
    ("Report Date", data.get("report_date") or "—"),
    ("Collection Date", data.get("collection_date") or "—"),
    ("Sample Type", data.get("sample_type") or "—"),
]

# Render as 3-column info grid
info_html_items = ""
for label, value in info_items:
    info_html_items += (
        f'<div style="padding:8px 0;">'
        f'  <div class="info-label">{label}</div>'
        f'  <div class="info-value">{value}</div>'
        f'</div>'
    )

st.markdown(
    f"""
    <div class="card" style="border-left:4px solid {COLORS['primary']};">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px 32px;">
            {info_html_items}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Report-level summary stats ────────────────────────────────────────────
total_tests = len(tests)
flagged_tests = sum(1 for t in tests if t.get("flag"))
normal_tests = total_tests - flagged_tests

c1, c2, c3 = st.columns(3)
c1.markdown(kpi_tile("Total Tests", total_tests, COLORS["primary"]), unsafe_allow_html=True)
c2.markdown(kpi_tile("Normal", normal_tests, COLORS["success"]), unsafe_allow_html=True)
c3.markdown(kpi_tile("Flagged", flagged_tests, COLORS["danger"] if flagged_tests else COLORS["success"]), unsafe_allow_html=True)

# ── CSV export ────────────────────────────────────────────────────────────
if tests:
    export_rows = []
    for t in tests:
        export_rows.append({
            "Test": t.get("test_name", ""),
            "Value": t.get("value", ""),
            "Unit": t.get("unit", ""),
            "Reference Range": t.get("reference_range", ""),
            "Flag": t.get("flag", ""),
            "Category": t.get("category", ""),
        })
    csv_buf = io.StringIO()
    pd.DataFrame(export_rows).to_csv(csv_buf, index=False)
    st.download_button(
        "⬇️ Download Report CSV",
        data=csv_buf.getvalue(),
        file_name=f"report_{doc_id[:8]}.csv",
        mime="text/csv",
    )

# Pie chart
if total_tests > 0:
    fig_pie = go.Figure(go.Pie(
        labels=["Normal", "Flagged"],
        values=[normal_tests, flagged_tests],
        hole=0.5,
        marker=dict(colors=[COLORS["success"], COLORS["danger"]]),
        textinfo="label+percent",
        textfont=dict(size=13),
    ))
    pie_layout = plotly_layout_defaults("Result Distribution", height=280)
    pie_layout["margin"] = dict(l=20, r=20, t=50, b=20)
    fig_pie.update_layout(**pie_layout, showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Test results grouped by category ──────────────────────────────────────
section_title("Test Results by Category")

grouped: dict[str, list] = defaultdict(list)
for t in tests:
    cat = t.get("category") or "Other"
    grouped[cat].append(t)

for cat in sorted(grouped.keys()):
    cat_tests = grouped[cat]
    cat_flagged = sum(1 for t in cat_tests if t.get("flag"))
    badge = f' <span class="flag-badge flag-high">{cat_flagged} flagged</span>' if cat_flagged else ""

    with st.expander(f"**{cat}** ({len(cat_tests)} tests){badge}", expanded=cat_flagged > 0):
        rows_html = ""
        for t in cat_tests:
            val = t.get("value")
            unit = t.get("unit") or ""
            ref = t.get("reference_range") or ""
            flag = t.get("flag")
            name = t.get("test_name", "")

            # Range indicator
            range_html = ""
            low, high = parse_reference_range(ref)
            fval = safe_float(val)
            if low is not None and high is not None and fval is not None and high > low:
                span = high - low
                pct = max(0, min(100, (fval - low) / span * 100))
                bar_color = COLORS["success"]
                if fval < low:
                    bar_color = COLORS["info"]
                    pct = 0
                elif fval > high:
                    bar_color = COLORS["danger"]
                    pct = 100
                range_html = (
                    f'<div style="width:100%;height:6px;background:{COLORS["border"]};border-radius:3px;position:relative;">'
                    f'  <div style="position:absolute;left:{pct}%;top:-3px;width:10px;height:10px;'
                    f'    border-radius:50%;background:{bar_color};transform:translateX(-50%);'
                    f'    box-shadow:0 0 0 2px white;"></div>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:0.68rem;color:{COLORS["text_muted"]};">'
                    f'  <span>{low}</span><span>{high}</span>'
                    f'</div>'
                )

            row_bg = COLORS["danger_light"] if flag else ""
            style_attr = f'background:{row_bg};' if row_bg else ""

            rows_html += f"""
            <tr style="{style_attr}">
                <td style="padding:8px 12px;font-weight:600;">{name}</td>
                <td style="padding:8px 12px;">{val or '—'}
                    <span style="color:{COLORS['text_muted']};font-size:0.8rem;">{unit}</span>
                </td>
                <td style="padding:8px 12px;color:{COLORS['text_muted']};font-size:0.85rem;">{ref}</td>
                <td style="padding:8px 12px;min-width:90px;">{range_html}</td>
                <td style="padding:8px 12px;">{flag_badge(flag)}</td>
            </tr>
            """

        st.markdown(
            f"""
            <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
                <thead>
                    <tr style="border-bottom:2px solid {COLORS['border']};text-align:left;">
                        <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;letter-spacing:0.04em;">Test</th>
                        <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Value</th>
                        <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Ref Range</th>
                        <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Position</th>
                        <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Status</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
