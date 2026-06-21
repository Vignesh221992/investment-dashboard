import streamlit as st

from dashboard_logic import render_home_page, run_script

st.set_page_config(page_title="Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("Tracker Tools")
st.sidebar.markdown("---")

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if st.sidebar.button("🚀 Mega-Cap ATH Scanner", use_container_width=True):
    st.session_state.current_page = "ATH"

if st.sidebar.button("📈 Nifty 50 Return Ranking", use_container_width=True):
    st.session_state.current_page = "Nifty"

if st.sidebar.button("📈 Nifty Smallcap 250 Ranking", use_container_width=True):
    st.session_state.current_page = "Smallcap250"

if st.session_state.current_page != "Home":
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Back to Home Landing Page", use_container_width=True):
        st.session_state.current_page = "Home"

if st.session_state.current_page == "Home":
    render_home_page()
elif st.session_state.current_page == "ATH":
    run_script("ATH_App.py")
elif st.session_state.current_page == "Nifty":
    run_script("Nifty50_Ranking.py")
elif st.session_state.current_page == "Smallcap250":
    run_script("NiftySmallcap250_Ranking.py")
