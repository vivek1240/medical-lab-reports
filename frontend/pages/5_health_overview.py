import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from collections import defaultdict

import plotly.graph_objects as go
import streamlit as st

from utils.api_client import (
    cached_biomarker_categories,
    cached_biomarker_summary,
    cached_trends_overview,
)
from utils.theme import (
    apply_theme,
    auth_guard,
    direction_arrow,
    flag_badge,
    get_colors,
    kpi_tile,
    plotly_layout_defaults,
    render_sidebar_profile,
    section_title,
)

st.set_page_config(page_title="Health Overview", page_icon="🩺", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

token = st.session_state.token

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">🩺 Health Overview</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        Your overall health score and actionable insights derived from your lab history.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Fetch data (cached) ─────────────────────────────────────────────────
s_ok, summary_rows = cached_biomarker_summary(token)
t_ok, trend_rows_raw = cached_trends_overview(token)
c_ok, cats_raw = cached_biomarker_categories(token)

if not s_ok:
    st.error("Failed to load biomarker data.")
    st.stop()
if not summary_rows:
    st.info("No biomarker data yet. Upload a report to see your health overview.")
    st.stop()

total = len(summary_rows)
flagged = sum(1 for r in summary_rows if r.get("flag"))
normal = total - flagged

# ── Health score gauge ────────────────────────────────────────────────────
health_score = round(100 - (flagged / total * 100)) if total > 0 else 100

gauge_left, gauge_right = st.columns([1, 2])

with gauge_left:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        number=dict(suffix="/100", font=dict(size=40, color=COLORS["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COLORS["border"]),
            bar=dict(color=COLORS["primary"], thickness=0.3),
            bgcolor="rgba(0,0,0,0)",
            steps=[
                dict(range=[0, 40], color="#FEE2E2"),
                dict(range=[40, 70], color="#FEF3C7"),
                dict(range=[70, 100], color="#D1FAE5"),
            ],
            threshold=dict(
                line=dict(color=COLORS["text"], width=3),
                thickness=0.8,
                value=health_score,
            ),
        ),
    ))
    gauge_layout = plotly_layout_defaults("", height=260)
    gauge_layout["margin"] = dict(l=30, r=30, t=20, b=10)
    fig_gauge.update_layout(**gauge_layout)
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Score interpretation
    if health_score >= 85:
        label, color, msg = "Excellent", COLORS["success"], "Most of your biomarkers are within normal ranges."
    elif health_score >= 70:
        label, color, msg = "Good", COLORS["primary"], "A few biomarkers need attention, but overall looking solid."
    elif health_score >= 50:
        label, color, msg = "Moderate", COLORS["warning"], "Several biomarkers are flagged. Consider reviewing with your doctor."
    else:
        label, color, msg = "Needs Attention", COLORS["danger"], "Many biomarkers are outside normal ranges. Medical review recommended."

    st.markdown(
        f"""
        <div class="card" style="border-left:4px solid {color};text-align:center;">
            <div style="font-size:1.1rem;font-weight:700;color:{color};">{label}</div>
            <div style="color:{COLORS['text_muted']};font-size:0.88rem;margin-top:4px;">{msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with gauge_right:
    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_tile("Total Tracked", total, COLORS["primary"]), unsafe_allow_html=True)
    c2.markdown(kpi_tile("Normal", normal, COLORS["success"]), unsafe_allow_html=True)
    c3.markdown(kpi_tile("Flagged", flagged, COLORS["danger"] if flagged else COLORS["success"]), unsafe_allow_html=True)

    # Category health mini-bars
    if c_ok and cats_raw:
        section_title("Category Breakdown")
        for cat in sorted(cats_raw, key=lambda c: c["flagged"], reverse=True):
            cat_name = cat["category"]
            cat_total = cat["total"]
            cat_flagged = cat["flagged"]
            cat_normal = cat["normal"]
            pct_normal = round(cat_normal / cat_total * 100) if cat_total else 100
            bar_color = COLORS["success"] if pct_normal >= 80 else COLORS["warning"] if pct_normal >= 50 else COLORS["danger"]

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:12px;margin:6px 0;">
                    <div style="width:140px;font-size:0.85rem;font-weight:600;color:{COLORS['text']};">{cat_name}</div>
                    <div style="flex:1;height:10px;background:{COLORS['border']};border-radius:5px;overflow:hidden;">
                        <div style="width:{pct_normal}%;height:100%;background:{bar_color};border-radius:5px;"></div>
                    </div>
                    <div style="min-width:80px;font-size:0.78rem;color:{COLORS['text_muted']};">{cat_normal}/{cat_total} normal</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── Actionable insights ──────────────────────────────────────────────────
section_title("Actionable Insights")

insights = []
trend_rows = trend_rows_raw if t_ok else []

if trend_rows:
    for tr in trend_rows:
        direction = tr.get("direction", "")
        delta = tr.get("delta_percent", 0)
        biomarker = tr.get("biomarker", "")
        latest_flag = tr.get("latest_flag")

        if direction == "up" and abs(delta) > 10:
            flag_note = " and is currently flagged" if latest_flag else ""
            insights.append({
                "icon": "🔺",
                "color": COLORS["danger"],
                "text": f"<strong>{biomarker}</strong> increased by {delta:+.1f}%{flag_note}. Consider monitoring closely.",
            })
        elif direction == "down" and abs(delta) > 10:
            if latest_flag:
                insights.append({
                    "icon": "🔻",
                    "color": COLORS["info"],
                    "text": f"<strong>{biomarker}</strong> decreased by {delta:+.1f}% and remains flagged.",
                })
            else:
                insights.append({
                    "icon": "✅",
                    "color": COLORS["success"],
                    "text": f"<strong>{biomarker}</strong> decreased by {delta:+.1f}% and is within normal range.",
                })

# Flagged biomarkers not in trends (single report)
flagged_names = {r.get("biomarker_name") for r in summary_rows if r.get("flag")}
trended_names = {tr.get("biomarker") for tr in trend_rows}
single_flagged = flagged_names - trended_names
for name in sorted(single_flagged):
    insights.append({
        "icon": "⚠️",
        "color": COLORS["warning"],
        "text": f"<strong>{name}</strong> is flagged but only has one data point. Upload more reports to track its trend.",
    })

if not insights:
    st.success("All your biomarkers look great! No concerning trends detected.")
else:
    for ins in insights[:12]:
        st.markdown(
            f"""
            <div class="info-card" style="border-left-color:{ins['color']};">
                <span style="font-size:1.1rem;">{ins['icon']}</span>
                <span style="margin-left:8px;">{ins['text']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Flagged biomarkers attention list ─────────────────────────────────────
section_title("Flagged Biomarkers — Attention List")

flagged_items = [r for r in summary_rows if r.get("flag")]
if not flagged_items:
    st.success("No flagged biomarkers. Everything is within normal ranges!")
else:
    trend_map = {tr["biomarker"]: tr for tr in trend_rows}

    table_html = ""
    for item in sorted(flagged_items, key=lambda x: x.get("biomarker_name", "")):
        name = item.get("biomarker_name", "")
        cat = item.get("category", "")
        val = item.get("latest_value", "—")
        unit = item.get("unit", "")
        ref = item.get("reference_range", "")
        flag = item.get("flag")
        report_date = item.get("report_date", "")

        trend_info = trend_map.get(name)
        if trend_info:
            dir_html = direction_arrow(trend_info.get("direction", "stable"))
            delta_val = trend_info.get("delta_percent", 0)
            delta_color = COLORS["danger"] if trend_info.get("direction") == "up" else COLORS["info"] if trend_info.get("direction") == "down" else COLORS["success"]
            delta_html = f'<span style="color:{delta_color};font-weight:600;">{delta_val:+.1f}%</span>'
        else:
            dir_html = '<span style="color:{};font-size:0.82rem;">—</span>'.format(COLORS["text_muted"])
            delta_html = "—"

        table_html += f"""
        <tr style="background:{COLORS['danger_light']};">
            <td style="padding:8px 12px;font-weight:600;">{name}</td>
            <td style="padding:8px 12px;font-size:0.85rem;color:{COLORS['text_muted']};">{cat}</td>
            <td style="padding:8px 12px;">{val} <span style="font-size:0.8rem;color:{COLORS['text_muted']};">{unit}</span></td>
            <td style="padding:8px 12px;font-size:0.85rem;color:{COLORS['text_muted']};">{ref}</td>
            <td style="padding:8px 12px;">{flag_badge(flag)}</td>
            <td style="padding:8px 12px;">{dir_html}</td>
            <td style="padding:8px 12px;">{delta_html}</td>
            <td style="padding:8px 12px;font-size:0.8rem;color:{COLORS['text_muted']};">{report_date}</td>
        </tr>
        """

    st.markdown(
        f"""
        <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
            <thead>
                <tr style="border-bottom:2px solid {COLORS['border']};text-align:left;">
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;letter-spacing:0.04em;">Biomarker</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Category</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Value</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Ref Range</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Status</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Direction</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Delta</th>
                    <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.73rem;text-transform:uppercase;">Date</th>
                </tr>
            </thead>
            <tbody>{table_html}</tbody>
        </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Category health heatmap ───────────────────────────────────────────────
section_title("Category Health Heatmap")

cat_date_groups: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"total": 0, "flagged": 0}))
for item in summary_rows:
    cat = item.get("category", "Other")
    rd = item.get("report_date") or "Unknown"
    cat_date_groups[cat][rd]["total"] += 1
    if item.get("flag"):
        cat_date_groups[cat][rd]["flagged"] += 1

if cat_date_groups:
    all_dates = sorted({d for cats in cat_date_groups.values() for d in cats.keys()})
    all_cats = sorted(cat_date_groups.keys())

    z_values = []
    hover_texts = []
    for cat in all_cats:
        row_z = []
        row_h = []
        for dt in all_dates:
            cell = cat_date_groups[cat].get(dt, {"total": 0, "flagged": 0})
            t, f = cell["total"], cell["flagged"]
            pct_normal = round((t - f) / t * 100) if t > 0 else 100
            row_z.append(pct_normal)
            row_h.append(f"{cat}<br>{dt}<br>{t - f}/{t} normal ({pct_normal}%)")
        z_values.append(row_z)
        hover_texts.append(row_h)

    fig_heatmap = go.Figure(go.Heatmap(
        z=z_values,
        x=all_dates,
        y=all_cats,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
        colorscale=[
            [0, COLORS["danger"]],
            [0.5, COLORS["warning"]],
            [1, COLORS["success"]],
        ],
        zmin=0,
        zmax=100,
        colorbar=dict(
            title=dict(text="% Normal", font=dict(size=12, color=COLORS["text"])),
            ticksuffix="%", thickness=15,
            tickfont=dict(size=11, color=COLORS["text"]),
        ),
    ))
    heatmap_layout = plotly_layout_defaults("", height=max(250, len(all_cats) * 40 + 80))
    heatmap_layout["yaxis"] = dict(
        automargin=True,
        tickfont=dict(size=12, color=COLORS["text"]),
        title=dict(font=dict(size=13, color=COLORS["text"])),
    )
    fig_heatmap.update_layout(**heatmap_layout, xaxis_title="Report Date")
    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.caption("Not enough data points to render the heatmap.")
