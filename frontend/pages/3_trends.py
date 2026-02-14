import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api_client import (
    cached_biomarker_history,
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
    parse_reference_range,
    plotly_layout_defaults,
    render_sidebar_profile,
    section_title,
)

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

token = st.session_state.token

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">📈 Trend Intelligence</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        Track how your biomarkers are changing between reports.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Fetch data (cached) ─────────────────────────────────────────────────
t_ok, all_rows = cached_trends_overview(token)
if not t_ok:
    st.error("Failed to load trend data.")
    st.stop()

if not all_rows:
    st.info("Not enough historical data yet. Upload at least 2 reports to see trends.")
    st.stop()

df_all = pd.DataFrame(all_rows)

# ── Sidebar filters ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Trend Filters")
    direction_filter = st.multiselect(
        "Direction",
        options=["up", "down", "stable"],
        default=["up", "down", "stable"],
    )
    category_values = sorted(df_all["category"].dropna().unique().tolist()) if "category" in df_all.columns else []
    if category_values:
        selected_categories = st.multiselect("Category", options=category_values, default=category_values)
    else:
        selected_categories = []

    delta_min = st.slider("Min |delta %|", 0.0, float(df_all["delta_percent"].abs().max()) if len(df_all) else 100.0, 0.0, 0.5)

# Apply filters
df = df_all.copy()
if direction_filter:
    df = df[df["direction"].isin(direction_filter)]
if selected_categories:
    df = df[df["category"].isin(selected_categories)]
df = df[df["delta_percent"].abs() >= delta_min]

# ── Date range filter ────────────────────────────────────────────────────
date_col = "latest_report_date" if "latest_report_date" in df.columns else None
if date_col:
    df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
    valid_dates = df["_parsed_date"].dropna()
    if not valid_dates.empty:
        mn = valid_dates.min().date()
        mx = valid_dates.max().date()
        if mn < mx:
            d1, d2 = st.columns(2)
            with d1:
                start = st.date_input("From", value=mn, min_value=mn, max_value=mx, key="trend_start")
            with d2:
                end = st.date_input("To", value=mx, min_value=mn, max_value=mx, key="trend_end")
            df = df[(df["_parsed_date"].dt.date >= start) & (df["_parsed_date"].dt.date <= end)]
    df = df.drop(columns=["_parsed_date"], errors="ignore")

if df.empty:
    st.info("No trend rows match the selected filters. Adjust sidebar filters.")
    st.stop()

# ── Summary callout boxes ─────────────────────────────────────────────────
rising = int((df["direction"] == "up").sum())
falling = int((df["direction"] == "down").sum())
stable = int((df["direction"] == "stable").sum())

c1, c2, c3 = st.columns(3)
c1.markdown(kpi_tile("Rising ▲", rising, COLORS["danger"]), unsafe_allow_html=True)
c2.markdown(kpi_tile("Falling ▼", falling, COLORS["info"]), unsafe_allow_html=True)
c3.markdown(kpi_tile("Stable ▶", stable, COLORS["success"]), unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Waterfall chart ───────────────────────────────────────────────────────
section_title("Biggest Movers")
top_n = df.head(15).copy()

fig_wf = go.Figure(go.Waterfall(
    orientation="h",
    y=top_n["biomarker"],
    x=top_n["delta_percent"],
    connector=dict(line=dict(color=COLORS["border"])),
    decreasing=dict(marker=dict(color=COLORS["info"])),
    increasing=dict(marker=dict(color=COLORS["danger"])),
    totals=dict(marker=dict(color=COLORS["success"])),
    texttemplate="%{x:.1f}%",
    textposition="outside",
))
wf_layout = plotly_layout_defaults("", height=max(300, len(top_n) * 32))
wf_layout["yaxis"] = dict(
    autorange="reversed", automargin=True,
    tickfont=dict(size=12, color=COLORS["text"]),
)
fig_wf.update_layout(**wf_layout, xaxis_title="Delta %", showlegend=False)
st.plotly_chart(fig_wf, use_container_width=True)

# ── Styled trend table ───────────────────────────────────────────────────
section_title("All Filtered Trends")

table_rows_html = ""
for _, row in df.iterrows():
    biomarker = row.get("biomarker", "")
    category = row.get("category", "")
    prev = row.get("previous")
    curr = row.get("current")
    delta = row.get("delta_percent", 0)
    direction = row.get("direction", "stable")
    latest_flag = row.get("latest_flag")
    prev_date = row.get("previous_report_date") or ""
    curr_date = row.get("latest_report_date") or ""

    # Mini bar
    bar_pct = min(abs(delta), 100)
    bar_color = COLORS["danger"] if direction == "up" else COLORS["info"] if direction == "down" else COLORS["success"]
    mini_bar = (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'  <div style="width:60px;height:6px;background:{COLORS["border"]};border-radius:3px;overflow:hidden;">'
        f'    <div style="width:{bar_pct}%;height:100%;background:{bar_color};border-radius:3px;"></div>'
        f'  </div>'
        f'  <span style="font-size:0.82rem;color:{bar_color};font-weight:600;">{delta:+.1f}%</span>'
        f'</div>'
    )

    row_bg = COLORS["danger_light"] if latest_flag else ""
    style = f"background:{row_bg};" if row_bg else ""

    table_rows_html += f"""
    <tr style="{style}">
        <td style="padding:8px 12px;font-weight:600;">{biomarker}</td>
        <td style="padding:8px 12px;font-size:0.85rem;color:{COLORS['text_muted']};">{category}</td>
        <td style="padding:8px 12px;">{prev if prev is not None else '—'}</td>
        <td style="padding:8px 12px;">{curr if curr is not None else '—'}</td>
        <td style="padding:8px 12px;">{mini_bar}</td>
        <td style="padding:8px 12px;">{direction_arrow(direction)}</td>
        <td style="padding:8px 12px;">{flag_badge(latest_flag)}</td>
        <td style="padding:8px 12px;font-size:0.78rem;color:{COLORS['text_muted']};">{prev_date}<br>{curr_date}</td>
    </tr>
    """

st.markdown(
    f"""
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
        <thead>
            <tr style="border-bottom:2px solid {COLORS['border']};text-align:left;">
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.04em;">Biomarker</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Category</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Previous</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Current</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Delta</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Direction</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Flag</th>
                <th style="padding:8px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.75rem;text-transform:uppercase;">Dates</th>
            </tr>
        </thead>
        <tbody>{table_rows_html}</tbody>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Trend drilldown ───────────────────────────────────────────────────────
section_title("Trend Drilldown")
candidates = df[df["biomarker_id"].notna()].copy()
if candidates.empty:
    st.caption("No canonical biomarker IDs available in filtered results.")
    st.stop()

candidates["biomarker_id"] = candidates["biomarker_id"].astype(int)
options = {
    f"{row.biomarker} | {row.category} | {row.delta_percent:+.1f}%": row.biomarker_id
    for row in candidates.itertuples(index=False)
}
choice = st.selectbox("Select biomarker for full history", list(options.keys()))
biomarker_id = options[choice]
h_ok, hist_rows = cached_biomarker_history(token, biomarker_id)
if not h_ok:
    st.error("Could not load history.")
    st.stop()

hist_df = pd.DataFrame(hist_rows)
if hist_df.empty:
    st.caption("No history for this biomarker.")
    st.stop()

hist_df["report_date"] = pd.to_datetime(hist_df["report_date"], errors="coerce")
hist_df = hist_df.sort_values("report_date")
plot_df = hist_df[hist_df["value"].notna()].copy()

if not plot_df.empty:
    # Try to get reference range from summary data
    sel_biomarker_name = choice.split("|")[0].strip()
    s_ok, summary_rows = cached_biomarker_summary(token)
    ref_low, ref_high = None, None
    if s_ok:
        for item in summary_rows:
            if item.get("biomarker_id") == biomarker_id:
                ref_low, ref_high = parse_reference_range(item.get("reference_range"))
                break

    fig_detail = go.Figure()

    if ref_low is not None and ref_high is not None:
        fig_detail.add_hrect(
            y0=ref_low, y1=ref_high,
            fillcolor="rgba(16,185,129,0.1)",
            line=dict(width=0),
            annotation_text="Normal range",
            annotation_position="top left",
            annotation=dict(font_size=10, font_color=COLORS["success"]),
        )

    marker_colors = []
    symbols = []
    for _, r in plot_df.iterrows():
        f = r.get("flag")
        if f and str(f).strip().upper() in ("H", "HIGH", "HH"):
            marker_colors.append(COLORS["danger"])
            symbols.append("triangle-up")
        elif f and str(f).strip().upper() in ("L", "LOW", "LL"):
            marker_colors.append(COLORS["info"])
            symbols.append("triangle-down")
        else:
            marker_colors.append(COLORS["primary"])
            symbols.append("circle")

    fig_detail.add_trace(go.Scatter(
        x=plot_df["report_date"],
        y=plot_df["value"],
        mode="lines+markers",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=10, color=marker_colors, symbol=symbols, line=dict(width=2, color="white")),
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "Value: %{y}<br>"
            "<extra></extra>"
        ),
    ))

    unit = plot_df["unit"].iloc[0] if "unit" in plot_df.columns and pd.notna(plot_df["unit"].iloc[0]) else ""
    fig_detail.update_layout(
        **plotly_layout_defaults(f"History: {sel_biomarker_name}", height=380),
        yaxis_title=unit or "Value",
        xaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig_detail, use_container_width=True)

display_cols = [c for c in ["report_date", "raw_value", "value", "unit", "flag", "doc_id"] if c in hist_df.columns]
st.dataframe(hist_df[display_cols], use_container_width=True, hide_index=True)
