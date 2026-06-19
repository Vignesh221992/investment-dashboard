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
    
    # Fetch S&P 500 components dynamically (kept strictly on one line to avoid SyntaxError)
    try:
        sp_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp_df = pd.read_csv(sp_url)
        if "Symbol" in sp_df.columns:
            allowed_tickers.update(sp_df["Symbol"].str.replace('.', '-').tolist())
    except Exception:
        pass
        
    # Fetch NASDAQ components dynamically
    try:
        nasdaq_url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.txt"
        res = requests.get(nasdaq_url, headers=headers, timeout=5)
        if res.status_code == 200:
            nas_tickers = [line.strip().upper() for line in res.text.splitlines() if line.strip()]
            allowed_tickers.update(nas_tickers)
    except Exception:
        pass
        
    return allowed_tickers


# --- API Streams: Fetching snapshots securely from Yahoo Finance Predefined Screeners ---
@st.cache_data(ttl=600)
def fetch_live_gainers_api(universe_pool):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
        params = {"scrIds": "day_gainers", "count": 150} 
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        
        parsed_results = []
        for q in quotes:
            symbol = q.get("symbol")
            mkt_cap_raw = q.get("marketCap", 0)
            mkt_cap_billions = mkt_cap_raw / 1e9 if mkt_cap_raw else 0
            
            if universe_pool and symbol not in universe_pool:
                continue
            if mkt_cap_billions < 50:
                continue
                
            parsed_results.append({
                "Symbol": symbol,
                "Name": q.get("shortName", "N/A"),
                "Sector": resolve_sector(symbol),
                "Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change ($)": round(q.get("regularMarketChange", 0), 2) if q.get("regularMarketChange") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(mkt_cap_billions, 2)
            })
            if len(parsed_results) >= 10:
                break
                
        if parsed_results:
            return pd.DataFrame(parsed_results)
    except Exception:
        pass
        
    return pd.DataFrame(columns=["Symbol", "Name", "Sector", "Price ($)", "Change ($)", "Change (%)", "Market Cap ($B)"])

@st.cache_data(ttl=600)
def fetch_live_trending_api(universe_pool):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
        params = {"scrIds": "most_actives", "count": 100}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        
        parsed_results = []
        for q in quotes:
            symbol = q.get("symbol")
            if universe_pool and symbol not in universe_pool:
                continue
                
            parsed_results.append({
                "Symbol": symbol,
                "Name": q.get("shortName", "N/A"),
                "Sector": resolve_sector(symbol),
                "Last Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else "N/A",
                "Volume": f"{q.get('regularMarketVolume', 0):,}" if q.get('regularMarketVolume') else "N/A"
            })
            if len(parsed_results) >= 10:
                break
                
        if parsed_results:
            return pd.DataFrame(parsed_results)
    except Exception:
        pass
        
    return pd.DataFrame(columns=["Symbol", "Name", "Sector", "Last Price ($)", "Change (%)", "Market Cap ($B)", "Volume"])


# --- Navigation Sidebar ---
st.sidebar.title("🎯 Alpha Tracker Tools")
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


# --- Main Dashboard Router ---
if st.session_state.current_page == "Home":
    st.caption("Live asset snapshots generated dynamically. Gainers are filtered for S&P 500/NASDAQ companies above $50B Market Cap.")
    
    # Generate the dynamic universe check constraints
    universe_pool = get_dynamic_allowed_universe()
    
    tab1, tab2 = st.tabs(["🔥 Top Gainers", "📊 Trending Tickers"])
    
    with tab1:
        st.subheader("Today's Top Market Gainers (>$50B Market Cap)")
        with st.spinner("Streaming filtered session gainers with sector mappings..."):
            live_gainers = fetch_live_gainers_api(universe_pool)
            st.dataframe(live_gainers, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("High-Volume Trending Tickers")
        with st.spinner("Streaming high-volume active assets with sector mappings..."):
            live_trending = fetch_live_trending_api(universe_pool)
            st.dataframe(live_trending, use_container_width=True, hide_index=True)

elif st.session_state.current_page == "ATH":
    run_script("ATH_App.py")

elif st.session_state.current_page == "Nifty":
    run_script("Nifty50_Ranking.py")

elif st.session_state.current_page == "Smallcap250":
    run_script("NiftySmallcap250_Ranking.py")