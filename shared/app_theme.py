"""App-specific theme overlay — sidebar tint + colored tabs + accent strip.

Call `inject_app_theme(primary, tint)` right after `inject_global_css()` in
each external app's app.py. Primary is the brand color (hex); tint is a very
light version of it used for the sidebar background and tab bar.

Examples:
    inject_app_theme("#2e7d32", "#e8f5e9")  # Pine Screener — forest green
    inject_app_theme("#00796b", "#e0f2f1")  # VL Tracker — teal
    inject_app_theme("#e65100", "#fff3e0")  # MarketSurge — deep orange
    inject_app_theme("#b06000", "#fff8e1")  # MSD Signals — amber gold
    inject_app_theme("#1565c0", "#e3f2fd")  # COT Tracker — deep navy
"""

from __future__ import annotations

import streamlit as st


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _darken(h: str, factor: float = 0.85) -> str:
    """Darken a hex color by the given factor (0..1)."""
    r, g, b = _hex_to_rgb(h)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def inject_app_theme(primary: str, tint: str, name: str = "App") -> None:
    """Inject app-specific theme CSS. primary = brand hex, tint = very light hex."""
    r, g, b = _hex_to_rgb(primary)
    primary_dark = _darken(primary, 0.80)
    primary_soft = f"rgba({r},{g},{b},0.10)"
    primary_hover = f"rgba({r},{g},{b},0.18)"

    css = f"""
    <style>
    /* ════ App theme: {name} ════ */

    /* Sidebar — soft tinted gradient with brand accent border */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {tint} 0%, #fbfcfd 85%) !important;
        border-right: 3px solid {primary} !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
        padding-top: 1rem !important;
    }}

    /* Top accent strip above main content */
    .stApp > header {{
        border-bottom: none !important;
    }}
    .block-container {{
        padding-top: 2rem !important;
    }}
    [data-testid="stAppViewContainer"] > section > div:first-child::before {{
        content: "";
        position: sticky;
        top: 0;
        display: block;
        height: 5px;
        background: linear-gradient(90deg, {primary} 0%, {primary} 65%, {tint} 100%);
        margin-bottom: 0;
        border-radius: 0 0 4px 4px;
    }}

    /* Tabs — colored active state with white text */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px !important;
        background: {tint} !important;
        padding: 6px 6px 0 6px !important;
        border-radius: 10px 10px 0 0 !important;
        border-bottom: 2px solid {primary} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        color: {primary_dark} !important;
        font-weight: 500 !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 16px !important;
        border-bottom: none !important;
        transition: background 0.15s ease, color 0.15s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: {primary_hover} !important;
        color: {primary_dark} !important;
    }}
    .stTabs [data-baseweb="tab"] p {{
        pointer-events: none !important;
        margin: 0 !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: {primary} !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-bottom-color: {primary} !important;
    }}
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] * {{
        color: #ffffff !important;
    }}

    /* Primary buttons adopt brand color */
    .stButton button[kind="primary"],
    .stLinkButton a[kind="primary"],
    [data-testid="stFormSubmitButton"] button {{
        background: {primary} !important;
        border-color: {primary} !important;
        color: #ffffff !important;
    }}
    .stButton button[kind="primary"]:hover,
    .stLinkButton a[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button:hover {{
        background: {primary_dark} !important;
        border-color: {primary_dark} !important;
    }}

    /* Secondary (outline) buttons — subtle brand tint on hover */
    .stButton button:not([kind="primary"]) {{
        border-color: {primary_soft} !important;
        color: {primary_dark} !important;
    }}
    .stButton button:not([kind="primary"]):hover {{
        background: {primary_hover} !important;
        border-color: {primary} !important;
        color: {primary_dark} !important;
    }}

    /* Metric labels in brand color */
    [data-testid="stMetricLabel"] {{
        color: {primary_dark} !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.78rem !important;
        letter-spacing: 0.04em;
    }}
    [data-testid="stMetricValue"] {{
        font-weight: 700 !important;
    }}

    /* Expander headers */
    .streamlit-expanderHeader {{
        color: {primary_dark} !important;
    }}

    /* Section dividers colored with brand */
    hr {{
        border: none !important;
        border-top: 1px solid {primary_soft} !important;
        margin: 1rem 0 !important;
    }}

    /* Radio / checkbox selected color */
    input[type="radio"]:checked + div > div:first-child,
    [data-testid="stRadio"] [aria-checked="true"] > div:first-child {{
        background: {primary} !important;
        border-color: {primary} !important;
    }}

    /* Links pick up brand color */
    a, a:visited {{
        color: {primary_dark} !important;
    }}
    a:hover {{
        color: {primary} !important;
    }}

    /* Dataframe header accent */
    [data-testid="stDataFrame"] thead tr th {{
        background: {tint} !important;
        color: {primary_dark} !important;
        font-weight: 600 !important;
        border-bottom: 2px solid {primary} !important;
    }}

    /* Focused inputs */
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    .stSelectbox [data-baseweb="select"]:focus-within > div {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 1px {primary} !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
