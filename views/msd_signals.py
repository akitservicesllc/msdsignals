"""
MSD Signals view — Multi-Signal Day detection from VL positioning.

Supports a date-range filter. When range == 1 day the layout matches the
classic single-day view; when range > 1 day a Date column is added and
rows are grouped (sorted) by date descending.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from shared.db import (
    get_etf_tickers,
    get_msd_available_dates,
    get_msd_latest_date,
    get_msd_signals_range,
    get_msd_summary_range,
)


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _load_dates() -> list[str]:
    return get_msd_available_dates(limit=180)


@st.cache_data(ttl=300)
def _load_signals(start: str, end: str, category: str | None) -> list[dict]:
    return get_msd_signals_range(start, end, category=category)


@st.cache_data(ttl=300)
def _load_summary(start: str, end: str) -> dict:
    return get_msd_summary_range(start, end)


@st.cache_data(ttl=300)
def _load_etf_tickers(start: str, end: str) -> set[str]:
    return get_etf_tickers(start, end)


def _top_print_price(prints: list[dict]) -> float | None:
    """Top print = lowest rank number (rank 1 is the most significant)."""
    if not prints:
        return None
    sorted_prints = sorted(
        prints,
        key=lambda p: int(p["r"]) if p.get("r") is not None else 9999,
    )
    return sorted_prints[0].get("price")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _format_currency(val) -> str:
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) >= 1_000_000_000:
            return f"${v/1e9:.1f}B"
        if abs(v) >= 1_000_000:
            return f"${v/1e6:.1f}M"
        if abs(v) >= 1_000:
            return f"${v/1e3:.1f}K"
        return f"${v:,.0f}"
    except (ValueError, TypeError):
        return str(val)


_CATEGORY_STYLE = {
    "STRONG":   ("#e6f4ea", "#137333", "⚡"),
    "TOP5_MSD": ("#e8f0fe", "#1967d2", "★"),
    "MSD":      ("#f1f3f4", "#5f6368", "●"),
}


def _category_badge(cat: str) -> str:
    bg, fg, icon = _CATEGORY_STYLE.get(cat, ("#f1f3f4", "#5f6368", "•"))
    return (
        f'<span style="background:{bg};color:{fg};padding:3px 10px;'
        f'border-radius:12px;font-weight:700;font-size:11px;'
        f'letter-spacing:0.03em;">{icon} {cat}</span>'
    )


def _rank_badge(rank) -> str:
    if rank is None:
        return "—"
    try:
        r = int(rank)
    except (ValueError, TypeError):
        return str(rank)
    if r <= 5:
        bg, fg = "#fce8e6", "#a50e0e"
    elif r <= 10:
        bg, fg = "#fef7e0", "#b06000"
    else:
        bg, fg = "#e8f0fe", "#1967d2"
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:10px;font-weight:700;font-size:11px;">#{r}</span>'
    )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render():
    st.markdown(
        "<h1 style='font-size:28px;margin:0 0 4px 0;'>🎯 MSD Signals</h1>"
        "<p style='color:#5f6368;font-size:13px;margin:0 0 20px 0;'>"
        "<b>Multi-Signal Day</b> — tickers with 2+ top-20 ranked VL positioning "
        "prints on the same day. <b>Strong Signal</b> fires when a rank≤5 print "
        "comes first, followed by a later rank≤20 print.</p>",
        unsafe_allow_html=True,
    )

    dates = _load_dates()
    if not dates:
        st.info(
            "No MSD data yet. Data populates after VL Tracker's daily "
            "4:00 PM CT job runs."
        )
        return

    # Range bounds come from whatever dates exist in DB
    min_avail = min(dates)
    max_avail = max(dates)

    # Default: last 7 available trading days
    default_end = max_avail
    default_start = dates[min(6, len(dates) - 1)] if len(dates) > 1 else max_avail

    # --- Controls row ---
    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
    with col1:
        try:
            date_range = st.date_input(
                "Date Range",
                value=(
                    date.fromisoformat(default_start),
                    date.fromisoformat(default_end),
                ),
                min_value=date.fromisoformat(min_avail),
                max_value=date.fromisoformat(max_avail),
                key="msd_range",
                format="YYYY-MM-DD",
            )
        except TypeError:
            # Older Streamlit without format kwarg
            date_range = st.date_input(
                "Date Range",
                value=(
                    date.fromisoformat(default_start),
                    date.fromisoformat(default_end),
                ),
                min_value=date.fromisoformat(min_avail),
                max_value=date.fromisoformat(max_avail),
                key="msd_range",
            )
    with col2:
        category_label = st.selectbox(
            "Category",
            options=["All", "STRONG", "TOP5_MSD", "MSD"],
            index=0,
            key="msd_category",
        )
    with col3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        hide_etfs = st.checkbox("Hide ETFs", value=False, key="msd_hide_etfs")
    with col4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("↻ Refresh", use_container_width=True, key="msd_refresh"):
            _load_dates.clear()
            _load_signals.clear()
            _load_summary.clear()
            _load_etf_tickers.clear()
            st.rerun()

    # Streamlit returns a tuple when 2 dates selected, single date while user
    # is mid-pick. Handle both.
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = (
            date_range if isinstance(date_range, date) else date.fromisoformat(default_start)
        )

    start_s = start_d.isoformat()
    end_s = end_d.isoformat()
    category = None if category_label == "All" else category_label
    show_date_col = start_s != end_s

    # --- Summary cards ---
    summary = _load_summary(start_s, end_s)
    total = summary.get("total", 0)
    strong = summary.get("strong", 0)
    top5 = summary.get("top5", 0)
    msd_only = summary.get("msd", 0)
    days = summary.get("days", 0)

    range_label = (
        f"{start_s}"
        if start_s == end_s
        else f"{start_s} → {end_s} ({days} day{'s' if days != 1 else ''})"
    )

    st.markdown(f"""
    <div style="display:flex;gap:14px;margin:4px 0 20px 0;flex-wrap:wrap;">
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #202124;">
            <div style="font-size:11px;color:#5F6368;font-weight:600;">{range_label}</div>
            <div style="font-size:12px;color:#5F6368;font-weight:600;margin-top:4px;">TOTAL MSDs</div>
            <div style="font-size:32px;font-weight:800;color:#202124;margin:6px 0;">{total}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #34A853;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">⚡ STRONG</div>
            <div style="font-size:32px;font-weight:800;color:#34A853;margin:6px 0;">{strong}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #4285F4;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">★ TOP5 MSD</div>
            <div style="font-size:32px;font-weight:800;color:#4285F4;margin:6px 0;">{top5}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #9AA0A6;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">● MSD</div>
            <div style="font-size:32px;font-weight:800;color:#5F6368;margin:6px 0;">{msd_only}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Table ---
    signals = _load_signals(start_s, end_s, category)
    if not signals:
        st.info(f"No MSDs matching filter between {start_s} and {end_s}.")
        return

    # Apply Hide ETFs filter
    if hide_etfs:
        etf_set = _load_etf_tickers(start_s, end_s)
        signals = [s for s in signals if s["ticker"] not in etf_set]
        if not signals:
            st.info("All matching rows are ETFs and were hidden by the filter.")
            return

    th_style = (
        'style="text-align:left;padding:10px 8px;color:#5F6368;font-size:11px;'
        'font-weight:700;text-transform:uppercase;letter-spacing:0.04em;"'
    )
    th_c = th_style.replace("text-align:left", "text-align:center")
    th_r = th_style.replace("text-align:left", "text-align:right")

    date_col_header = f"<th {th_style}>Date</th>" if show_date_col else ""
    header = (
        '<table style="width:100%;border-collapse:collapse;font-size:13px;'
        'font-family:\'Inter\',sans-serif;">'
        '<thead>'
        '<tr style="background:#F8F9FA;border-bottom:2px solid #DADCE0;">'
        f'{date_col_header}'
        f'<th {th_style}>Ticker</th>'
        f'<th {th_style}>Category</th>'
        f'<th {th_r}>Score</th>'
        f'<th {th_c}>Hits</th>'
        f'<th {th_c}>Best</th>'
        f'<th {th_r}>TP</th>'
        f'<th {th_style}>First Print</th>'
        f'<th {th_style}>Last Print</th>'
        f'<th {th_r}>$ Total</th>'
        f'<th {th_style}>Sector</th>'
        '</tr></thead><tbody>'
    )
    body_rows: list[str] = []
    for row in signals:
        ticker = row["ticker"]
        sector = row.get("sector") or "—"
        hits = row.get("hit_count") or 0
        best = row.get("best_rank")
        score = row.get("score") or 0
        fp_time = (row.get("first_print_time") or "")[:8] or "—"
        fp_rank = row.get("first_print_rank")
        lp_time = (row.get("last_print_time") or "")[:8] or "—"
        lp_rank = row.get("last_print_rank")
        total_dol = _format_currency(row.get("total_dollars"))
        cat_html = _category_badge(row.get("category") or "MSD")
        tp = _top_print_price(row.get("prints") or [])
        tp_cell = f"${tp:,.2f}" if tp else "—"
        date_cell = (
            f'<td style="padding:10px 8px;color:#5f6368;font-family:monospace;'
            f'font-size:12px;">{row.get("trade_date")}</td>'
            if show_date_col else ""
        )

        body_rows.append(
            f'<tr style="border-bottom:1px solid #F1F3F4;">'
            f'{date_cell}'
            f'<td style="padding:10px 8px;font-weight:700;color:#202124;'
            f'font-size:14px;">{ticker}</td>'
            f'<td style="padding:10px 8px;">{cat_html}</td>'
            f'<td style="padding:10px 8px;text-align:right;font-weight:700;'
            f'color:#202124;">{score:.0f}</td>'
            f'<td style="padding:10px 8px;text-align:center;">{hits}</td>'
            f'<td style="padding:10px 8px;text-align:center;">{_rank_badge(best)}</td>'
            f'<td style="padding:10px 8px;text-align:right;color:#202124;'
            f'font-family:monospace;">{tp_cell}</td>'
            f'<td style="padding:10px 8px;">{_rank_badge(fp_rank)} '
            f'<span style="color:#5f6368;">{fp_time}</span></td>'
            f'<td style="padding:10px 8px;">{_rank_badge(lp_rank)} '
            f'<span style="color:#5f6368;">{lp_time}</span></td>'
            f'<td style="padding:10px 8px;text-align:right;color:#202124;">{total_dol}</td>'
            f'<td style="padding:10px 8px;color:#5f6368;font-size:12px;">{sector}</td>'
            f'</tr>'
        )
    table_html = header + "".join(body_rows) + "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # --- Drill-down ---
    st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
    with st.expander(
        f"Print timeline drill-down ({len(signals)} rows)",
        expanded=False,
    ):
        for row in signals:
            ticker = row["ticker"]
            prints = row.get("prints") or []
            if not prints:
                continue
            lines: list[str] = []
            for p in prints:
                t = p.get("t") or "—"
                r = p.get("r")
                price = p.get("price")
                vol = p.get("vol")
                dp = "DP" if p.get("dp") else ""
                sw = "SWP" if p.get("sw") else ""
                flags = " ".join(x for x in (dp, sw) if x)
                flag_html = (
                    f' <span style="color:#a50e0e;font-weight:600;font-size:10px;">{flags}</span>'
                    if flags else ""
                )
                price_s = f"${price}" if price else ""
                vol_s = f"{int(vol):,}" if vol else ""
                lines.append(
                    f'<div style="padding:4px 0;border-bottom:1px dashed #f1f3f4;">'
                    f'<span style="color:#5f6368;font-family:monospace;">{t}</span> '
                    f'{_rank_badge(r)} '
                    f'<span style="color:#202124;">{price_s}</span> '
                    f'<span style="color:#9aa0a6;">&middot; {vol_s}</span>'
                    f'{flag_html}</div>'
                )
            st.markdown(
                f'<div style="padding:12px 16px;background:#F8F9FA;border-radius:8px;'
                f'margin-bottom:10px;">'
                f'<div style="font-weight:700;font-size:15px;color:#202124;'
                f'margin-bottom:8px;">{ticker} '
                f'<span style="font-weight:400;color:#5f6368;font-size:12px;">'
                f'— {row.get("trade_date")} · {row.get("category")} '
                f'· score {row.get("score"):.0f}</span></div>'
                + "".join(lines) +
                '</div>',
                unsafe_allow_html=True,
            )

    # --- Footer ---
    computed_at = signals[0].get("computed_at") if signals else ""
    st.markdown(
        f'<div style="margin-top:20px;padding-top:12px;border-top:1px solid #dadce0;'
        f'color:#9aa0a6;font-size:11px;text-align:right;">'
        f'MSDs computed at {computed_at} UTC &middot; '
        f'source: VL Tracker positioning_trades (rank ≤ 20 threshold)'
        f'</div>',
        unsafe_allow_html=True,
    )
