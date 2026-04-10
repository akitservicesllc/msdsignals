"""
Global CSS Design System for VL Tracker.
Google-inspired clean design with vibrant Google logo colors.

Import and call inject_global_css() once from app.py after st.set_page_config().
"""

import streamlit as st


# =============================================================================
# DESIGN TOKENS  (Google palette)
# =============================================================================

COLORS = {
    # Google primary colors
    "primary":       "#4285F4",   # Google Blue
    "primary_light": "#34A853",   # Google Green

    # Semantic — Google palette
    "bull":          "#34A853",   # Google Green
    "bull_bg":       "#e6f4ea",
    "bull_fg":       "#137333",
    "bear":          "#EA4335",   # Google Red
    "bear_bg":       "#fce8e6",
    "bear_fg":       "#a50e0e",
    "neutral_bg":    "#f1f3f4",
    "neutral_fg":    "#5f6368",
    "warn_bg":       "#fef7e0",
    "warn_fg":       "#b06000",

    # Surfaces — Google clean white
    "surface":       "#ffffff",
    "surface_alt":   "#f8f9fa",
    "border":        "#dadce0",
    "border_light":  "#f1f3f4",

    # Text — Google grey scale
    "text":          "#202124",
    "text_muted":    "#9aa0a6",
    "text_subtle":   "#5f6368",
}

# Google logo vibrant colors for charts
GOOGLE_CHART_COLORS = ["#4285F4", "#EA4335", "#FBBC05", "#34A853"]

RADIUS = {
    "sm":  "8px",
    "md":  "12px",
    "lg":  "16px",
    "xl":  "20px",
    "pill": "9999px",
}


# =============================================================================
# GLOBAL CSS — Google-inspired clean design
# =============================================================================

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

/* ── Global reset ── */
.stApp {
    font-family: 'Inter', 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #ffffff;
}
#MainMenu { visibility: hidden; }
footer   { visibility: hidden; }

/* ── Header: transparent, hide deploy chrome ── */
header[data-testid="stHeader"] {
    background: transparent !important;
    backdrop-filter: none !important;
}
header[data-testid="stHeader"] .stAppDeployButton {
    display: none !important;
}
[data-testid="stToolbarActions"] {
    display: none !important;
}

/* ── Content padding ── */
.block-container { padding-top: 1rem; padding-bottom: 1rem; }

/* ── Sidebar styling ── */
section[data-testid="stSidebar"] {
    background: #f8f9fa;
    border-right: 1px solid #dadce0;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1rem;
}

/* ── Expander styling (Google-clean) ── */
.streamlit-expanderHeader {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #202124 !important;
}

/* ── Badge utility classes — Google palette ── */
.vl-badge-bull {
    background: #e6f4ea; color: #137333;
    padding: 4px 14px; border-radius: 20px;
    font-weight: 600; font-size: 12px; letter-spacing: 0.02em;
    display: inline-block;
}
.vl-badge-bear {
    background: #fce8e6; color: #a50e0e;
    padding: 4px 14px; border-radius: 20px;
    font-weight: 600; font-size: 12px; letter-spacing: 0.02em;
    display: inline-block;
}
.vl-badge-neutral {
    background: #f1f3f4; color: #5f6368;
    padding: 4px 14px; border-radius: 20px;
    font-weight: 600; font-size: 12px; letter-spacing: 0.02em;
    display: inline-block;
}
.vl-badge-dp {
    background: #e8f0fe; color: #1a73e8;
    padding: 2px 8px; border-radius: 8px;
    font-size: 11px; font-weight: 600;
    display: inline-block;
}
.vl-badge-sweep {
    background: #fef7e0; color: #b06000;
    padding: 2px 8px; border-radius: 8px;
    font-size: 11px; font-weight: 600;
    display: inline-block;
}

/* ── Section headers ── */
.vl-section-header {
    font-size: 11px; color: #9aa0a6; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Google-style card shadow ── */
.vl-card {
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 8px;
    box-shadow: 0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
    transition: box-shadow 0.2s ease;
}
.vl-card:hover {
    box-shadow: 0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15);
}

/* ── Tabs — Google Material style ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    border-bottom: 1px solid #dadce0;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500 !important;
    color: #5f6368 !important;
    border-bottom: 3px solid transparent;
    padding: 8px 16px !important;
    cursor: pointer !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #4285F4 !important;
    background: #f8f9fa !important;
}
.stTabs [data-baseweb="tab"] * {
    cursor: pointer !important;
    pointer-events: none !important;
}
.stTabs [data-baseweb="tab"] {
    pointer-events: auto !important;
}
.stTabs [data-baseweb="tab"] p {
    pointer-events: none !important;
    margin: 0 !important;
}
.stTabs [aria-selected="true"] {
    color: #4285F4 !important;
    border-bottom-color: #4285F4 !important;
    font-weight: 600 !important;
}

/* ── Mobile responsive ── */
@media (max-width: 768px) {
    header[data-testid="stHeader"]       { z-index: 999 !important; }
    section[data-testid="stSidebar"]     { z-index: 1000 !important; }
    [data-testid="stSidebarCollapsedControl"] { z-index: 1002 !important; }
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
"""


def inject_global_css():
    """Call once from app.py after st.set_page_config()."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
