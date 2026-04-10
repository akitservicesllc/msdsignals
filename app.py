"""
MSD Signals — Standalone Streamlit App

Surfaces Multi-Signal Day detections from VL Tracker positioning data plus
Cluster Bombs analytics. Reads two read-only DBs synced from MAG:

    /home/data/pine_screener.db   -> msd_trades
    /home/data/vl_tracker.db      -> cluster_bombs

Runs on Azure App Service (msdsignals-vinapp.azurewebsites.net) under the
shared MarketAIGenie-plan.
"""

import streamlit as st

# Page config must be first Streamlit call
st.set_page_config(
    page_title="MSD Signals",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from shared.styles import inject_global_css  # noqa: E402
from views.msd_signals import render as render_msd  # noqa: E402
from views.cluster_bombs import render as render_cluster_bombs  # noqa: E402

inject_global_css()

APP_VERSION = "v1.0"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:0 0 14px 0;border-bottom:1px solid #dadce0;margin-bottom:18px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:26px;">🎯</span>
            <div>
                <div style="font-size:18px;font-weight:700;color:#202124;">
                    MSD Signals
                </div>
                <div style="font-size:11px;color:#9aa0a6;">
                    AK IT Services &middot; {APP_VERSION}
                </div>
            </div>
        </div>
        <div style="font-size:11px;color:#9aa0a6;">
            Data source: VL Tracker &middot; Pine Screener
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Top-level tabs
# ---------------------------------------------------------------------------
tab_msd, tab_cluster = st.tabs(["🎯 MSD Signals", "💥 Cluster Bombs"])

with tab_msd:
    render_msd()

with tab_cluster:
    render_cluster_bombs()
