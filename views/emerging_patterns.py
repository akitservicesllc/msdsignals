"""
Emerging Patterns view — VL Top 5 × MarketSurge × News cross-join.

Categories (priority order):
    GOLDEN  -> VL top5 AND in MS top_10_groups same date
    MS+VL   -> VL top5 AND in any other MS screen same date
    NEWS+VL -> VL top5 AND news catalyst (urgency >= 7) same date
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from shared.db import get_emerging_patterns, get_emerging_summary, MS_SCREEN_DISPLAY


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _load_patterns(start: str, end: str) -> list[dict]:
    return get_emerging_patterns(start, end)


@st.cache_data(ttl=300)
def _load_summary(start: str, end: str) -> dict:
    return get_emerging_summary(start, end)


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
    "GOLDEN":  ("#fef7e0", "#b06000", "🏆"),
    "MS+VL":   ("#e8f0fe", "#1967d2", "📈"),
    "NEWS+VL": ("#e6f4ea", "#137333", "📰"),
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
    bg, fg = "#fce8e6", "#a50e0e"  # all are rank <= 5
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:10px;font-weight:700;font-size:11px;">#{r}</span>'
    )


def _screen_pills(screens: list[str]) -> str:
    pills: list[str] = []
    for s in screens:
        if s == "Top 10 Groups":
            bg, fg = "#fef7e0", "#b06000"  # gold
        else:
            bg, fg = "#e8f0fe", "#1967d2"  # blue
        pills.append(
            f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:10px;font-size:10px;font-weight:600;'
            f'margin-right:4px;white-space:nowrap;">{s}</span>'
        )
    return " ".join(pills)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render():
    st.markdown(
        "<h1 style='font-size:28px;margin:0 0 4px 0;'>🔥 Emerging Patterns</h1>"
        "<p style='color:#5f6368;font-size:13px;margin:0 0 20px 0;'>"
        "VL Top 5 ranked prints cross-referenced against MarketSurge screens + News catalysts. "
        "<b>GOLDEN</b> = VL top5 + MS Top 10 Industry Group. "
        "<b>MS+VL</b> = VL top5 + any MS scan. "
        "<b>NEWS+VL</b> = VL top5 + high-quality news.</p>",
        unsafe_allow_html=True,
    )

    # --- Controls ---
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        today = date.today()
        default_end = today
        default_start = today - timedelta(days=30)
        try:
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
                min_value=date(2026, 3, 1),
                max_value=today,
                key="ep_range",
                format="YYYY-MM-DD",
            )
        except TypeError:
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
                min_value=date(2026, 3, 1),
                max_value=today,
                key="ep_range",
            )
    with col2:
        cat_label = st.selectbox(
            "Category",
            options=["All", "GOLDEN", "MS+VL", "NEWS+VL"],
            index=0,
            key="ep_category",
        )
    with col3:
        if st.button("↻ Refresh", use_container_width=True, key="ep_refresh"):
            _load_patterns.clear()
            _load_summary.clear()
            st.rerun()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d = end_d = (
            date_range if isinstance(date_range, date) else default_start
        )

    start_s = start_d.isoformat()
    end_s = end_d.isoformat()

    # --- Summary cards ---
    summary = _load_summary(start_s, end_s)
    total = summary.get("total", 0)
    golden = summary.get("golden", 0)
    ms_vl = summary.get("ms_vl", 0)
    news_vl = summary.get("news_vl", 0)
    days = summary.get("days", 0)

    range_label = (
        f"{start_s}" if start_s == end_s
        else f"{start_s} → {end_s} ({days} day{'s' if days != 1 else ''})"
    )

    st.markdown(f"""
    <div style="display:flex;gap:14px;margin:4px 0 20px 0;flex-wrap:wrap;">
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #202124;">
            <div style="font-size:11px;color:#5F6368;font-weight:600;">{range_label}</div>
            <div style="font-size:12px;color:#5F6368;font-weight:600;margin-top:4px;">TOTAL</div>
            <div style="font-size:32px;font-weight:800;color:#202124;margin:6px 0;">{total}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #F9AB00;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">🏆 GOLDEN</div>
            <div style="font-size:32px;font-weight:800;color:#F9AB00;margin:6px 0;">{golden}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #4285F4;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">📈 MS+VL</div>
            <div style="font-size:32px;font-weight:800;color:#4285F4;margin:6px 0;">{ms_vl}</div>
        </div>
        <div style="flex:1;min-width:150px;background:#F8F9FA;border-radius:10px;padding:18px;
                    text-align:center;border-top:4px solid #34A853;">
            <div style="font-size:12px;color:#5F6368;font-weight:600;">📰 NEWS+VL</div>
            <div style="font-size:32px;font-weight:800;color:#34A853;margin:6px 0;">{news_vl}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Table ---
    patterns = _load_patterns(start_s, end_s)
    if cat_label != "All":
        patterns = [p for p in patterns if p["category"] == cat_label]

    if not patterns:
        st.info(f"No emerging patterns matching filter between {start_s} and {end_s}.")
        return

    th = (
        'style="text-align:left;padding:10px 8px;color:#5F6368;font-size:11px;'
        'font-weight:700;text-transform:uppercase;letter-spacing:0.04em;"'
    )
    th_c = th.replace("text-align:left", "text-align:center")
    th_r = th.replace("text-align:left", "text-align:right")

    header = (
        '<table style="width:100%;border-collapse:collapse;font-size:13px;'
        'font-family:\'Inter\',sans-serif;">'
        '<thead>'
        '<tr style="background:#F8F9FA;border-bottom:2px solid #DADCE0;">'
        f'<th {th}>Date</th>'
        f'<th {th}>Ticker</th>'
        f'<th {th}>Signal</th>'
        f'<th {th_c}>VL Rank</th>'
        f'<th {th_c}>Prints</th>'
        f'<th {th_r}>$ Volume</th>'
        f'<th {th}>MS Screens / News</th>'
        f'<th {th}>Sector</th>'
        '</tr></thead><tbody>'
    )

    body_rows: list[str] = []
    for row in patterns:
        cat_html = _category_badge(row["category"])
        rank_html = _rank_badge(row["best_rank"])
        dol = _format_currency(row["total_dollars"])

        # Build match detail
        details: list[str] = []
        if row["ms_screens"]:
            details.append(_screen_pills(row["ms_screens"]))
        if row["news_items"]:
            for ni in row["news_items"][:2]:
                u = ni.get("urgency") or 0
                cat = ni.get("category") or ""
                hl = (ni.get("headline") or "")[:80]
                details.append(
                    f'<div style="margin-top:4px;">'
                    f'<span style="background:#e6f4ea;color:#137333;padding:1px 6px;'
                    f'border-radius:8px;font-size:10px;font-weight:600;">'
                    f'📰 {u:.0f} · {cat}</span> '
                    f'<span style="color:#202124;font-size:12px;">{hl}</span></div>'
                )
        detail_html = "".join(details) or "—"

        body_rows.append(
            f'<tr style="border-bottom:1px solid #F1F3F4;">'
            f'<td style="padding:10px 8px;color:#5f6368;font-family:monospace;'
            f'font-size:12px;">{row["trade_date"]}</td>'
            f'<td style="padding:10px 8px;font-weight:700;color:#202124;'
            f'font-size:14px;">{row["ticker"]}</td>'
            f'<td style="padding:10px 8px;">{cat_html}</td>'
            f'<td style="padding:10px 8px;text-align:center;">{rank_html}</td>'
            f'<td style="padding:10px 8px;text-align:center;">{row["vl_prints"]}</td>'
            f'<td style="padding:10px 8px;text-align:right;color:#202124;">{dol}</td>'
            f'<td style="padding:10px 8px;">{detail_html}</td>'
            f'<td style="padding:10px 8px;color:#5f6368;font-size:12px;">'
            f'{row["sector"] or "—"}</td>'
            f'</tr>'
        )

    table_html = header + "".join(body_rows) + "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # --- Footer ---
    st.markdown(
        f'<div style="margin-top:20px;padding-top:12px;border-top:1px solid #dadce0;'
        f'color:#9aa0a6;font-size:11px;text-align:right;">'
        f'Emerging Patterns: VL rank ≤ 5 × MS scans × News (urgency ≥ 7) '
        f'&middot; same-date join &middot; {len(patterns)} results'
        f'</div>',
        unsafe_allow_html=True,
    )
