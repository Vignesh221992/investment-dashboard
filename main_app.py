import streamlit as st

from dashboard_logic import render_home_page, run_script

st.set_page_config(page_title="Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root {
        --app-bg: #0b1220;
        --surface: #0f172a;
        --surface-2: #132344;
        --surface-3: #0d1424;
        --text: #eef4ff;
        --muted: #9fb3da;
        --border: #23375c;
        --button-bg: #0f1a32;
        --button-hover: #11294a;
        --input-bg: #0f172a;
        --input-text: #eef4ff;
        --tab-bg: #0f1a32;
        --tab-active: #11294a;
    }

    @media (prefers-color-scheme: light) {
        :root {
            --app-bg: #f8fafc;
            --surface: #ffffff;
            --surface-2: #eef4ff;
            --surface-3: #f8fafc;
            --text: #0f172a;
            --muted: #475569;
            --border: #cbd5e1;
            --button-bg: #f8fafc;
            --button-hover: #e2e8f0;
            --input-bg: #ffffff;
            --input-text: #0f172a;
            --tab-bg: #f8fafc;
            --tab-active: #e0edff;
        }
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--app-bg) !important;
        color: var(--text) !important;
    }

    [data-testid="stHeader"] {
        background: var(--surface) !important;
        color: var(--text) !important;
    }

    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] section {
        background: var(--surface) !important;
    }

    [data-testid="stSidebar"] button {
        color: var(--text) !important;
        background: var(--button-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"] button:hover {
        background: var(--button-hover) !important;
    }

    h1, h2, h3, h4, h5, p, span, div, label, li {
        color: var(--text) !important;
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stMultiselect"] label {
        color: var(--text) !important;
        font-weight: 600;
    }

    div[data-testid="stSelectbox"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] div[role="button"],
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stMultiselect"] > div,
    div[data-testid="stMultiselect"] div[role="button"] {
        background: var(--input-bg) !important;
        color: var(--input-text) !important;
        border: 1px solid var(--border) !important;
        box-shadow: none !important;
    }

    div[data-testid="stSelectbox"] div[role="listbox"],
    div[data-baseweb="popover"],
    ul[role="listbox"],
    div[role="listbox"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }

    div[data-testid="stSelectbox"] li,
    div[data-testid="stSelectbox"] div[role="option"],
    div[role="option"] {
        background: var(--surface) !important;
        color: var(--text) !important;
    }

    div[data-testid="stSelectbox"] li:hover,
    div[data-testid="stSelectbox"] div[role="option"]:hover,
    div[role="option"]:hover {
        background: var(--surface-2) !important;
    }

    button[kind="primary"],
    button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background: var(--button-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }

    .stTabs [role="tablist"] {
        gap: 0.35rem;
    }

    .stTabs [role="tab"] {
        background: var(--tab-bg);
        color: var(--muted);
        border: 1px solid var(--border);
        border-radius: 8px 8px 0 0;
    }

    .stTabs [role="tab"][aria-selected="true"] {
        background: var(--tab-active);
        color: var(--text);
        border-color: var(--border);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("Tracker Tools")
st.sidebar.markdown("---")

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if st.sidebar.button("🚀 Mega-Cap ATH Scanner", use_container_width=True):
    st.session_state.current_page = "ATH"

if st.sidebar.button("📈 NIFTY Ranking", use_container_width=True):
    st.session_state.current_page = "NiftyRanking"

if st.session_state.current_page != "Home":
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Back to Home Landing Page", use_container_width=True):
        st.session_state.current_page = "Home"

if st.session_state.current_page == "Home":
    render_home_page()
elif st.session_state.current_page == "ATH":
    run_script("ATH_App.py")
elif st.session_state.current_page == "NiftyRanking":
    st.subheader("NIFTY Ranking")
    tab1, tab2 = st.tabs(["Nifty 50", "Nifty Smallcap 250"])
    with tab1:
        run_script("Nifty50_Ranking.py")
    with tab2:
        run_script("NiftySmallcap250_Ranking.py")
