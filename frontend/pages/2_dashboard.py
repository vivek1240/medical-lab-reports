import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.api_client import (
    ApiClient,
    cached_biomarker_categories,
    cached_biomarker_history,
    cached_biomarker_summary,
    cached_biomarker_unmapped,
)
from utils.theme import (
    PLOTLY_COLORS,
    apply_theme,
    auth_guard,
    flag_badge,
    get_colors,
    kpi_tile,
    parse_reference_range,
    pill_tag,
    plotly_layout_defaults,
    render_sidebar_profile,
    safe_float,
    section_title,
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
apply_theme()
auth_guard()
render_sidebar_profile()
COLORS = get_colors()

token = st.session_state.token
client = ApiClient(token=token)

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="margin-bottom:4px;">
        <span style="font-size:1.6rem;font-weight:800;color:{COLORS['text']};">📊 Biomarker Dashboard</span>
    </div>
    <p style="color:{COLORS['text_muted']};margin-top:0;">
        Your latest biomarker readings at a glance, grouped by category.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Fetch data (cached) ─────────────────────────────────────────────────
s_ok, rows = cached_biomarker_summary(token)
if not s_ok:
    st.error("Failed to load biomarker data.")
    st.stop()
if not rows:
    st.info("No biomarker data yet. Upload a report first.")
    st.stop()

c_ok, cats_list = cached_biomarker_categories(token)
if not c_ok:
    st.error("Failed to load category data.")
    st.stop()

df = pd.DataFrame(rows)
cats_df = pd.DataFrame(cats_list)

# ── Biomarker search ─────────────────────────────────────────────────────
search_query = st.text_input(
    "🔍 Search biomarkers",
    placeholder="Type a biomarker name…",
    key="bio_search",
)

if search_query:
    mask = df["biomarker_name"].str.contains(search_query, case=False, na=False)
    df = df[mask]
    if df.empty:
        st.warning(f"No biomarkers match **{search_query}**.")
        st.stop()

# ── Date range filter ────────────────────────────────────────────────────
if "report_date" in df.columns:
    df["_parsed_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    valid_dates = df["_parsed_date"].dropna()
    if not valid_dates.empty:
        min_dt = valid_dates.min().date()
        max_dt = valid_dates.max().date()
        if min_dt < max_dt:
            date_left, date_right = st.columns(2)
            with date_left:
                start = st.date_input("From", value=min_dt, min_value=min_dt, max_value=max_dt, key="dash_start")
            with date_right:
                end = st.date_input("To", value=max_dt, min_value=min_dt, max_value=max_dt, key="dash_end")
            df = df[(df["_parsed_date"].dt.date >= start) & (df["_parsed_date"].dt.date <= end)]
    df = df.drop(columns=["_parsed_date"], errors="ignore")

# ── KPI row ───────────────────────────────────────────────────────────────
total = len(df)
flagged = int(df["flag"].notna().sum())
normal = total - flagged
unclassified = int(df["biomarker_id"].isna().sum())

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_tile("Total Biomarkers", total, COLORS["primary"]), unsafe_allow_html=True)
c2.markdown(kpi_tile("Normal", normal, COLORS["success"]), unsafe_allow_html=True)
c3.markdown(kpi_tile("Flagged", flagged, COLORS["danger"] if flagged else COLORS["success"]), unsafe_allow_html=True)
c4.markdown(kpi_tile("Unmapped", unclassified, COLORS["warning"] if unclassified else COLORS["success"]), unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── CSV export ────────────────────────────────────────────────────────────
export_df = df[[c for c in ["biomarker_name", "latest_value", "unit", "reference_range", "flag", "category", "report_date"] if c in df.columns]]
csv_buf = io.StringIO()
export_df.to_csv(csv_buf, index=False)
st.download_button(
    "⬇️ Download CSV",
    data=csv_buf.getvalue(),
    file_name="biomarker_dashboard.csv",
    mime="text/csv",
)

# ── Radar + Category bar ─────────────────────────────────────────────────
if not cats_df.empty:
    left, right = st.columns(2)

    with left:
        section_title("Category Health Fingerprint")
        radar_cats = cats_df.copy()
        radar_cats["pct_normal"] = (radar_cats["normal"] / radar_cats["total"] * 100).round(1)
        categories_list = radar_cats["category"].tolist()
        values = radar_cats["pct_normal"].tolist()
        # close the polygon
        categories_list_closed = categories_list + [categories_list[0]]
        values_closed = values + [values[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_list_closed,
            fill="toself",
            fillcolor="rgba(13,148,136,0.15)",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=6, color=COLORS["primary"]),
            name="% Normal",
        ))
        fig_radar.update_layout(
            **plotly_layout_defaults("", height=370),
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%",
                                tickfont=dict(size=10, color=COLORS["text"])),
                angularaxis=dict(tickfont=dict(size=11, color=COLORS["text"])),
            ),
            showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with right:
        section_title("Normal vs Flagged by Category")
        sorted_cats = cats_df.sort_values("flagged", ascending=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=sorted_cats["category"], x=sorted_cats["normal"],
            orientation="h", name="Normal",
            marker_color=COLORS["success"],
        ))
        fig_bar.add_trace(go.Bar(
            y=sorted_cats["category"], x=sorted_cats["flagged"],
            orientation="h", name="Flagged",
            marker_color=COLORS["danger"],
        ))
        bar_layout = plotly_layout_defaults("", height=370)
        bar_layout["yaxis"] = dict(
            automargin=True,
            tickfont=dict(size=12, color=COLORS["text"]),
        )
        fig_bar.update_layout(**bar_layout, barmode="stack", xaxis_title="Count")
        st.plotly_chart(fig_bar, use_container_width=True)

# ── Category drill-down ───────────────────────────────────────────────────
section_title("Biomarker Details by Category")

categories = sorted(df["category"].dropna().unique().tolist())
selected_category = st.selectbox("Select category", categories, label_visibility="collapsed")
filtered = df[df["category"] == selected_category].copy()

# Build styled HTML table
table_rows_html = ""
for _, row in filtered.iterrows():
    val = row.get("latest_value")
    unit = row.get("unit") or ""
    ref = row.get("reference_range") or ""
    flag = row.get("flag")
    name = row.get("biomarker_name", "")
    report_date = row.get("report_date") or ""

    # Range bar
    range_bar_html = ""
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
        range_bar_html = (
            f'<div style="width:100%;height:8px;background:{COLORS["border"]};border-radius:4px;position:relative;">'
            f'  <div style="position:absolute;left:{pct}%;top:-2px;width:12px;height:12px;'
            f'    border-radius:50%;background:{bar_color};transform:translateX(-50%);"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;font-size:0.7rem;color:{COLORS["text_muted"]};">'
            f'  <span>{low}</span><span>{high}</span>'
            f'</div>'
        )

    row_bg = COLORS["danger_light"] if flag else ""
    style = f'background:{row_bg};' if row_bg else ""

    table_rows_html += f"""
    <tr style="{style}">
        <td style="padding:10px 12px;font-weight:600;">{name}</td>
        <td style="padding:10px 12px;">{val or '—'} <span style="color:{COLORS['text_muted']};font-size:0.82rem;">{unit}</span></td>
        <td style="padding:10px 12px;font-size:0.85rem;color:{COLORS['text_muted']};">{ref}</td>
        <td style="padding:10px 12px;min-width:100px;">{range_bar_html}</td>
        <td style="padding:10px 12px;">{flag_badge(flag)}</td>
        <td style="padding:10px 12px;color:{COLORS['text_muted']};font-size:0.82rem;">{report_date}</td>
    </tr>
    """

st.markdown(
    f"""
    <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
        <thead>
            <tr style="border-bottom:2px solid {COLORS['border']};text-align:left;">
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;letter-spacing:0.04em;">Biomarker</th>
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;">Value</th>
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;">Ref Range</th>
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;">Range Position</th>
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;">Status</th>
                <th style="padding:10px 12px;color:{COLORS['text_muted']};font-weight:600;font-size:0.78rem;text-transform:uppercase;">Date</th>
            </tr>
        </thead>
        <tbody>{table_rows_html}</tbody>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Trend drilldown with reference band ───────────────────────────────────
section_title("Biomarker Trend Drilldown")
history_candidates = filtered[filtered["biomarker_id"].notna()].copy()
if not history_candidates.empty:
    history_candidates["biomarker_id"] = history_candidates["biomarker_id"].astype(int)
    options = {
        f"{row.biomarker_name}": row.biomarker_id
        for row in history_candidates.itertuples(index=False)
    }
    selected = st.selectbox("Select biomarker to view trend", list(options.keys()))
    biomarker_id = options[selected]

    # Find reference range for this biomarker
    sel_row = history_candidates[history_candidates["biomarker_id"] == biomarker_id].iloc[0]
    ref_low, ref_high = parse_reference_range(sel_row.get("reference_range"))

    h_ok, hist_rows = cached_biomarker_history(token, biomarker_id)
    if h_ok:
        hist_df = pd.DataFrame(hist_rows)
        if not hist_df.empty:
            hist_df["report_date"] = pd.to_datetime(hist_df["report_date"], errors="coerce")
            hist_df = hist_df.sort_values("report_date")
            plot_df = hist_df[hist_df["value"].notna()].copy()
            if not plot_df.empty:
                fig_trend = go.Figure()

                # Reference range band
                if ref_low is not None and ref_high is not None:
                    fig_trend.add_hrect(
                        y0=ref_low, y1=ref_high,
                        fillcolor="rgba(16,185,129,0.1)",
                        line=dict(width=0),
                        annotation_text="Normal range",
                        annotation_position="top left",
                        annotation=dict(font_size=10, font_color=COLORS["success"]),
                    )

                # Determine marker colors by flag
                marker_colors = []
                for _, r in plot_df.iterrows():
                    f = r.get("flag")
                    if f and str(f).strip().upper() in ("H", "HIGH", "HH"):
                        marker_colors.append(COLORS["danger"])
                    elif f and str(f).strip().upper() in ("L", "LOW", "LL"):
                        marker_colors.append(COLORS["info"])
                    else:
                        marker_colors.append(COLORS["primary"])

                fig_trend.add_trace(go.Scatter(
                    x=plot_df["report_date"],
                    y=plot_df["value"],
                    mode="lines+markers",
                    line=dict(color=COLORS["primary"], width=2.5),
                    marker=dict(size=10, color=marker_colors, line=dict(width=2, color="white")),
                    hovertemplate=(
                        "<b>%{x|%b %d, %Y}</b><br>"
                        "Value: %{y}<br>"
                        "<extra></extra>"
                    ),
                    name=selected,
                ))

                unit = plot_df["unit"].iloc[0] if "unit" in plot_df.columns else ""
                fig_trend.update_layout(
                    **plotly_layout_defaults(f"{selected} Over Time", height=380),
                    yaxis_title=unit or "Value",
                    xaxis_title="",
                    showlegend=False,
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            # History table
            display_cols = [c for c in ["report_date", "raw_value", "value", "unit", "flag", "doc_id"] if c in hist_df.columns]
            st.dataframe(hist_df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.error("Could not load biomarker history.")
else:
    st.caption("No mapped biomarkers in this category to show trend for.")

# ── Unmapped tests ────────────────────────────────────────────────────────
with st.expander("⚠️ Unmapped / Unclassified Tests", expanded=False):
    u_ok, unmapped_rows = cached_biomarker_unmapped(token)
    if u_ok:
        if unmapped_rows:
            pills_html = " ".join(
                pill_tag(f"{r['test_name']} ({r['count']})", warning=True) for r in unmapped_rows
            )
            st.markdown(pills_html, unsafe_allow_html=True)
        else:
            st.success("All tests are mapped to canonical biomarkers!")
    else:
        st.caption("Could not load unmapped tests.")
