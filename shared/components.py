"""
Reusable UI components for VL Tracker.
Badges, cards, metric displays, refresh timestamps.
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from shared.styles import COLORS

ET = ZoneInfo("America/New_York")


def signal_badge(label: str) -> str:
    """Return HTML for a signal badge (bull/bear/neutral)."""
    label_upper = label.upper().strip()
    if label_upper in ("BULL", "BULLISH", "BUY", "LONG"):
        css = "vl-badge-bull"
    elif label_upper in ("BEAR", "BEARISH", "SELL", "SHORT"):
        css = "vl-badge-bear"
    else:
        css = "vl-badge-neutral"
    return f'<span class="{css}">{label_upper}</span>'


def dp_badge() -> str:
    """Return HTML badge for Dark Pool tag."""
    return '<span class="vl-badge-dp">DP</span>'


def sweep_badge() -> str:
    """Return HTML badge for Sweep tag."""
    return '<span class="vl-badge-sweep">SWEEP</span>'


def format_dollars(val) -> str:
    """Format dollar amounts: $1.2M, $500K, etc."""
    if val is None:
        return "—"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return "—"
    if abs(val) >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


def format_price(val) -> str:
    """Format price with $ and 2 decimals."""
    if val is None:
        return "—"
    try:
        return f"${float(val):,.2f}"
    except (ValueError, TypeError):
        return "—"


def format_volume(val) -> str:
    """Format volume with commas."""
    if val is None:
        return "—"
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return "—"


def section_header(text: str):
    """Render a small uppercase section header."""
    st.markdown(f'<p class="vl-section-header">{text}</p>', unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = None, color: str = None):
    """Render a Google-style metric card using HTML."""
    delta_html = ""
    if delta:
        delta_color = color or COLORS["text_subtle"]
        delta_html = f'<div style="font-size:13px;color:{delta_color};margin-top:2px;">{delta}</div>'

    html = f"""
    <div class="vl-card" style="padding:16px 20px;text-align:center;">
        <div style="font-size:12px;color:{COLORS['text_muted']};text-transform:uppercase;
                    letter-spacing:0.05em;font-weight:600;">{label}</div>
        <div style="font-size:28px;font-weight:700;color:{COLORS['text']};margin-top:4px;">
            {value}
        </div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _format_scrape_label(scrape_time: str) -> str:
    """Format scrape time as ET string with relative age."""
    dt_utc = datetime.fromisoformat(scrape_time).replace(tzinfo=timezone.utc)
    dt_et = dt_utc.astimezone(ET)
    now_et = datetime.now(ET)
    diff = now_et - dt_et
    if diff.total_seconds() < 3600:
        ago = f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        ago = f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        ago = f"{int(diff.days)}d ago"
    return f"Last scraped: {dt_et.strftime('%b %d, %Y %I:%M %p')} ET ({ago})"


def render_last_scraped(scrape_time: str = None):
    """Show a 'Last scraped' badge in the sidebar."""
    if not scrape_time:
        st.caption("Last scraped: Never")
        return
    try:
        st.caption(_format_scrape_label(scrape_time))
    except Exception:
        st.caption(f"Last scraped: {scrape_time}")


def render_last_scraped_topright(scrape_time: str = None):
    """Render a fixed 'Last scraped' badge in the top-right corner of the main area."""
    if not scrape_time:
        label = "Last scraped: Never"
    else:
        try:
            label = _format_scrape_label(scrape_time)
        except Exception:
            label = f"Last scraped: {scrape_time}"

    st.markdown(f"""
    <div style="position:fixed;top:14px;right:24px;z-index:999;
                font-size:12px;color:{COLORS['text_muted']};
                background:{COLORS['surface']};padding:6px 14px;
                border-radius:8px;border:1px solid {COLORS['border']};
                font-family:'Google Sans','Inter',sans-serif;
                box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        {label}
    </div>
    """, unsafe_allow_html=True)
