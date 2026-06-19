import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Page Layout Setup
st.set_page_config(page_title="Alpha Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Helper Function to Dynamically Execute Sub-Scripts ---
def run_script(script_path):
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Strip out any secondary set_page_config commands to prevent Streamlit from crashing
        clean_lines = []
        for line in code.splitlines():
            if "st.set_page_config" not in line:
                clean_lines.append(line)
        clean_code = "\n".join(clean_lines)
        
        # Execute script code cleanly in the shared environment namespace
        exec(clean_code, globals())
    except Exception as e:
        st.error(f"Failed to load module script dynamically: {e}")

# --- High-Performance Sector Map for Large/Mega Caps ---
MEGA_CAP_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AMZN": "Consumer Cyclical",
    "META": "Communication Services", "GOOGL": "Communication Services", "GOOG": "Communication Services",
    "BRK-B": "Financial Services", "LLY": "Healthcare", "AVGO": "Technology", "TSLA": "Consumer Cyclical",
    "UNH": "Healthcare", "V": "Financial Services", "JPM": "Financial Services", "XOM": "Energy",
    "MA": "Financial Services", "PG": "Consumer Defensive", "COST": "Consumer Defensive",
    "JNJ": "Healthcare", "HD": "Consumer Cyclical", "ORCL": "Technology", "NFLX": "Communication Services",
    "MRK": "Healthcare", "CVX": "Energy", "AMD": "Technology", "CRM": "Technology", "NOW": "Technology"
}

@st.cache_data(ttl=86400)
def resolve_sector(symbol):
    """Resolves sector via optimized dictionary map or quick yfinance lookup fallback."""
    symbol_upper = symbol.upper()
    if symbol_upper in MEGA_CAP_SECTORS:
        return MEGA_CAP_SECTORS[symbol_upper]
    try:
        ticker = yf.Ticker(symbol)
        sector = ticker.info.get("sector", "Financials/Other")
        return sector
    except Exception:
        return "Technology" # Smart default fallback for tech/enterprise screens

# --- 100% Dynamic Universe Generator ---
@st.cache_data(ttl=86400) 
def get_dynamic_allowed_universe():
    allowed_tickers = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Fetch S&P 500 components dynamically
    try:
        sp_url = "