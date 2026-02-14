"""
Report Comparison – side-by-side view of two lab reports with
difference highlighting for overlapping tests.
"""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import plotly.graph_objects as go
import streamlit as st

from utils.api_client import cached_report_detail, cached_reports
from utils.theme import (
    apply_theme,
    auth_guard,
    flag_badge,
    get_colors,
    kpi_tile,
    plotly_layout_defaults,
    render_sidebar_profile,
    safe_float,
    section_title,
)

st.set_page_config(page_title="Compare Reports", page_icon="🔀", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

token = st.session_state.token

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">🔀 Report Comparison</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        Select two reports to compare side-by-side. Overlapping tests are highlighted with delta values.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Report list ──────────────────────────────────────────────────────────
r_ok, reports = cached_reports(token)
if not r_ok:
    st.error("Failed to load reports.")
    st.stop()
if not reports or len(reports) < 2:
    st.info("You need at least 2 uploaded reports to use comparison. Upload more reports first.")
    st.stop()

label_map = {
    f"{r.get('report_date') or 'No date'} — {r.get('lab_name') or 'Unknown'} — {r.get('patient_name', '')}": r["doc_id"]
    for r in reports
}
labels = list(label_map.keys())

col_a, col_b = st.columns(2)
with col_a:
    choice_a = st.selectbox("Report A (older)", labels, index=min(1, len(labels) - 1), key="cmp_a")
with col_b:
    choice_b = st.selectbox("Report B (newer)", labels, index=0, key="cmp_b")

doc_a = label_map[choice_a]
doc_b = label_map[choice_b]

if doc_a == doc_b:
    st.warning("Please select two **different** reports to compare.")
    st.stop()

# ── Fetch both reports (cached) ──────────────────────────────────────────
a_ok, data_a = cached_report_detail(token, doc_a)
b_ok, data_b = cached_report_detail(token, doc_b)

if not a_ok or not b_ok:
    st.error("Failed to load one or both report details.")
    st.stop()

tests_a = data_a.get("test_results", [])
tests_b = data_b.get("test_results", [])

# ── Summary KPIs ─────────────────────────────────────────────────────────
def _summarize(tests):
    total = len(tests)
    flagged = sum(1 for t in tests if t.get("flag"))
    return total, total - flagged, flagged

ta, na, fa = _summarize(tests_a)
tb, nb, fb = _summarize(tests_b)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

kpi_left, kpi_right = st.columns(2)
with kpi_left:
    st.markdown(f"<div style='text-align:center;font-weight:700;color:{COLORS['text']};margin-bottom:8px;'>Report A</div>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.markdown(kpi_tile("Tests", ta, COLORS["primary"]), unsafe_allow_html=True)
    k2.markdown(kpi_tile("Normal", na, COLORS["success"]), unsafe_allow_html=True)
    k3.markdown(kpi_tile("Flagged", fa, COLORS["danger"] if fa else COLORS["success"]), unsafe_allow_html=True)
with kpi_right:
    st.markdown(f"<div style='text-align:center;font-weight:700;color:{COLORS['text']};margin-bottom:8px;'>Report B</div>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.markdown(kpi_tile("Tests", tb, COLORS["primary"]), unsafe_allow_html=True)
    k2.markdown(kpi_tile("Normal", nb, COLORS["success"]), unsafe_allow_html=True)
    k3.markdown(kpi_tile("Flagged", fb, COLORS["danger"] if fb else COLORS["success"]), unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Build test lookup ────────────────────────────────────────────────────
def _test_key(t):
    """Normalised test name for matching."""
    return (t.get("test_name") or "").strip().lower()

map_a = {_test_key(t): t for t in tests_a}
map_b = {_test_key(t): t for t in tests_b}

all_keys = sorted(set(map_a.keys()) | set(map_b.keys()))
common_keys = sorted(set(map_a.keys()) & set(map_b.keys()))
only_a = sorted(set(map_a.keys()) - set(map_b.keys()))
only_b = sorted(set(map_b.keys()) - set(map_a.keys()))

# ── Comparison chart – overlapping tests ─────────────────────────────────
if common_keys:
    section_title("Overlapping Tests — Delta Chart")

    names, vals_a_list, vals_b_list, deltas = [], [], [], []
    for k in common_keys:
        va = safe_float(map_a[k].get("value"))
        vb = safe_float(map_b[k].get("value"))
        if va is not None and vb is not None:
            names.append(map_a[k].get("test_name", k))
            vals_a_list.append(va)
            vals_b_list.append(vb)
            deltas.append(vb - va)

    if names:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Report A",
            x=names,
            y=vals_a_list,
            marker_color=COLORS["info"],
        ))
        fig.add_trace(go.Bar(
            name="Report B",
            x=names,
            y=vals_b_list,
            marker_color=COLORS["primary"],
        ))
        layout = plotly_layout_defaults("Value Comparison", height=max(350, len(names) * 18 + 100))
        layout["xaxis"] = dict(
            tickfont=dict(size=10, color=COLORS["text"]),
            title=dict(font=dict(size=13, color=COLORS["text"])),
            tickangle=-45,
        )
        fig.update_layout(**layout, barmode="group")
        st.plotly_chart(fig, use_container_width=True)

# ── Side-by-side table ───────────────────────────────────────────────────
section_title("Full Side-by-Side Comparison")

rows_html = ""
for k in all_keys:
    ta_item = map_a.get(k)
    tb_item = map_b.get(k)
    name = (ta_item or tb_item or {}).get("test_name", k)
    unit = (ta_item or tb_item or {}).get("unit", "")

    va_str = ta_item.get("value", "—") if ta_item else "—"
    vb_str = tb_item.get("value", "—") if tb_item else "—"
    flag_a = flag_badge(ta_item.get("flag")) if ta_item else "—"
    flag_b = flag_badge(tb_item.get("flag")) if tb_item else "—"

    # Delta
    va_f = safe_float(va_str) if ta_item else None
    vb_f = safe_float(vb_str) if tb_item else None
    if va_f is not None and vb_f is not None:
        delta_val = vb_f - va_f
        if delta_val > 0:
            delta_html = f'<span style="color:{COLORS["danger"]};font-weight:600;">+{delta_val:.2f}</span>'
        elif delta_val < 0:
            delta_html = f'<span style="color:{COLORS["info"]};font-weight:600;">{delta_val:.2f}</span>'
        else:
            delta_html = f'<span style="color:{COLORS["success"]};font-weight:600;">0</span>'
    else:
        delta_html = "—"

    # Row background
    row_bg = ""
    if not ta_item:
        row_bg = f"background:{COLORS['info_light']};"
    elif not tb_item:
        row_bg = f"background:{COLORS['warning_light']};"

    rows_html += f"""
    <tr style="{row_bg}">
        <td style="padding:8px 12px;font-weight:600;">{name}</td>
        <td style="padding:8px 12px;">{va_str} <span style="font-size:0.8rem;color:{COLORS['text_muted']};">{unit}</span></td>
        <td style="padding:8px 12px;">{flag_a}</td>
        <td style="padding:8px 12px;">{vb_str} <span style="font-size:0.8rem;color:{COLORS['text_muted']};">{unit}</span></td>
        <td style="padding:8px 12px;">{flag_b}</td>
        <td style="padding:8px 12px;">{delta_html}</td>
    </tr>
    """

st.markdown(
    f"""
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
        <thead>
            <tr style="border-bottom:2px solid {COLORS['border']};text-align:left;">
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;letter-spacing:0.04em;">Test</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">A Value</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">A Flag</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">B Value</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">B Flag</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Delta (B−A)</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Legend ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-top:12px;font-size:0.8rem;color:{COLORS['text_muted']};">
        <span style="display:inline-block;width:12px;height:12px;background:{COLORS['info_light']};border:1px solid {COLORS['border']};border-radius:3px;margin-right:4px;vertical-align:middle;"></span> Only in Report B &nbsp;&nbsp;
        <span style="display:inline-block;width:12px;height:12px;background:{COLORS['warning_light']};border:1px solid {COLORS['border']};border-radius:3px;margin-right:4px;vertical-align:middle;"></span> Only in Report A
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Stats callout ────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.markdown(kpi_tile("Common Tests", len(common_keys), COLORS["primary"]), unsafe_allow_html=True)
c2.markdown(kpi_tile("Only in A", len(only_a), COLORS["warning"]), unsafe_allow_html=True)
c3.markdown(kpi_tile("Only in B", len(only_b), COLORS["info"]), unsafe_allow_html=True)
