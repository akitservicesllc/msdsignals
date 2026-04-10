"""
Cluster Bombs view — ported from VL Tracker.

Reads vl_tracker.db.cluster_bombs (synced to /home/data/ by MAG's
cross_app_sync). "Today" sub-tab shows the latest date's cluster bombs,
"History" sub-tab shows multi-day analytics.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from shared.db import get_cluster_bomb_rows, get_cluster_bomb_available_dates
from shared.components import format_dollars, format_volume, section_header, metric_card
from shared.styles import GOOGLE_CHART_COLORS


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _load_dates() -> list[str]:
    return get_cluster_bomb_available_dates()


@st.cache_data(ttl=300)
def _load_rows(trade_date: str | None) -> list[dict]:
    return get_cluster_bomb_rows(trade_date=trade_date, limit=5000)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render():
    st.markdown(
        "<h1 style='font-size:28px;margin:0 0 4px 0;'>💥 Cluster Bombs</h1>"
        "<p style='color:#5f6368;font-size:13px;margin:0 0 20px 0;'>"
        "Multiple large positioning trades on the same ticker within a tight "
        "time window — high-conviction institutional activity.</p>",
        unsafe_allow_html=True,
    )

    tab_today, tab_history = st.tabs(["Today", "History"])
    with tab_today:
        _render_today()
    with tab_history:
        _render_history()


def _render_today():
    dates = _load_dates()
    if not dates:
        st.info("No cluster bomb data yet. Data populates after VL Tracker's "
                "daily 4:00 PM CT job.")
        return

    selected_date = st.selectbox(
        "Select Date",
        options=dates,
        index=0,
        format_func=lambda d: f"{d} {'(Today)' if d == date.today().isoformat() else ''}",
        key="cb_date",
    )

    rows = _load_rows(selected_date)
    if not rows:
        st.info(f"No cluster bombs for {selected_date}")
        return

    df = pd.DataFrame(rows)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Cluster Bombs", str(len(df)))
    with col2:
        total_vol = df["total_volume"].sum() if "total_volume" in df.columns else 0
        metric_card("Total Volume", format_volume(total_vol))
    with col3:
        total_dollars = df["total_dollars"].sum() if "total_dollars" in df.columns else 0
        metric_card("Total Dollars", format_dollars(total_dollars))
    with col4:
        unique_tickers = df["ticker"].nunique()
        metric_card("Unique Tickers", str(unique_tickers))

    st.markdown("")

    # Table
    section_header("Cluster Bomb Details")
    display_cols = ["time_range", "ticker", "sector", "cluster_size",
                    "total_volume", "total_dollars", "avg_price"]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].copy()

    if "total_dollars" in display_df.columns:
        display_df["total_dollars"] = display_df["total_dollars"].apply(format_dollars)
    if "total_volume" in display_df.columns:
        display_df["total_volume"] = display_df["total_volume"].apply(format_volume)
    if "avg_price" in display_df.columns:
        display_df["avg_price"] = display_df["avg_price"].apply(
            lambda v: f"${v:,.2f}" if v else "—"
        )

    col_names = {
        "time_range": "Time Range", "ticker": "Ticker", "sector": "Sector",
        "cluster_size": "Cluster Size", "total_volume": "Volume",
        "total_dollars": "Dollars", "avg_price": "Avg Price",
    }
    display_df.columns = [col_names.get(c, c.replace("_", " ").title())
                          for c in display_df.columns]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Top tickers bar chart
    if len(df) > 1 and "total_dollars" in df.columns:
        section_header("Top Tickers by Dollar Volume")
        ticker_dollars = (
            df.groupby("ticker")["total_dollars"].sum()
              .sort_values(ascending=True).tail(10)
        )
        fig = px.bar(
            x=ticker_dollars.values,
            y=ticker_dollars.index,
            orientation="h",
            color_discrete_sequence=[GOOGLE_CHART_COLORS[2]],
        )
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Total Dollars",
            yaxis_title="Ticker",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})

    # Sector breakdown pie
    if "sector" in df.columns and df["sector"].notna().any():
        section_header("Sector Breakdown")
        sector_counts = df["sector"].value_counts()
        fig = px.pie(
            names=sector_counts.index,
            values=sector_counts.values,
            color_discrete_sequence=GOOGLE_CHART_COLORS,
        )
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        fig.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})


def _render_history():
    rows = _load_rows(None)
    if not rows:
        st.info("No historical cluster bomb data available.")
        return

    df = pd.DataFrame(rows)
    if df["trade_date"].nunique() < 2:
        st.info("Need at least 2 days of data for historical analysis.")
        return

    all_dates = sorted(df["trade_date"].unique())
    col1, col2 = st.columns(2)
    with col1:
        start = st.selectbox("Start Date", options=all_dates, index=0, key="cb_hist_start")
    with col2:
        end = st.selectbox("End Date", options=all_dates,
                           index=len(all_dates) - 1, key="cb_hist_end")

    df = df[(df["trade_date"] >= start) & (df["trade_date"] <= end)]
    if df.empty:
        st.info("No data in the selected range.")
        return

    # Daily count trend
    section_header("Daily Cluster Bomb Count")
    daily = df.groupby("trade_date").size().reset_index(name="count")
    daily = daily.sort_values("trade_date")
    fig = px.line(
        daily, x="trade_date", y="count", markers=True,
        color_discrete_sequence=[GOOGLE_CHART_COLORS[2]],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Date",
        yaxis_title="Count",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Most frequent tickers
    section_header("Most Frequent Tickers")
    ticker_freq = df.groupby("ticker").agg(
        appearances=("trade_date", "nunique"),
        total_dollars=("total_dollars", "sum"),
    ).sort_values("appearances", ascending=False).head(15).reset_index()
    ticker_freq["total_dollars"] = ticker_freq["total_dollars"].apply(format_dollars)
    ticker_freq.columns = ["Ticker", "Days Seen", "Total Dollars"]
    st.dataframe(ticker_freq, use_container_width=True, hide_index=True)

    # Daily dollar volume
    if "total_dollars" in df.columns:
        section_header("Daily Dollar Volume")
        daily_vol = df.groupby("trade_date")["total_dollars"].sum().reset_index()
        daily_vol = daily_vol.sort_values("trade_date")
        fig = px.bar(
            daily_vol, x="trade_date", y="total_dollars",
            color_discrete_sequence=[GOOGLE_CHART_COLORS[3]],
        )
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Date",
            yaxis_title="Total Dollars",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
