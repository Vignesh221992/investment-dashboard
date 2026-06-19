import streamlit as st
import pandas as pd
import requests

# 1. Page Layout Setup
st.set_page_config(page_title="Alpha Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Helper Function to Dynamically Execute Sub-Scripts without page_config conflicts ---
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

# --- 100% Dynamic Universe Generator: Fetching lists live from data-center friendly endpoints ---
@st.cache_data(ttl=86400) # Cache for 24 hours to maximize performance
def get_dynamic_allowed_universe():
    allowed_tickers = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 1. Fetch S&P 500 components dynamically from an open data repository
    try:
        sp_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp_df = pd.read_csv(sp_url)
        if "Symbol" in sp_df.columns:
            allowed_tickers.update(sp_df["Symbol"].str.replace('.', '-').tolist())
    except Exception:
        pass
        
    # 2. Fetch NASDAQ components dynamically from an open financial dataset stream
    try:
        nasdaq_url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.txt"
        res = requests.get(nasdaq_url, headers=headers, timeout=5)
        if res.status_code == 200:
            nas_tickers = [line.strip().upper() for line in res.text.splitlines() if line.strip()]
            allowed_tickers.update(nas_tickers)
    except Exception:
        pass
        
    return allowed_tickers


# --- API Streams: Fetching completely dynamic screener snapshots via Yahoo Finance ---
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
            
            # Apply index filter only if the live reference lists loaded successfully
            if universe_pool and symbol not in universe_pool:
                continue
                
            parsed_results.append({
                "Symbol": symbol,
                "Name": q.get("shortName", "N/A"),
                "Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change ($)": round(q.get("regularMarketChange", 0), 2) if q.get("regularMarketChange") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else "N/A"
            })
            if len(parsed_results) >= 10:
                break
                
        if parsed_results:
            return pd.DataFrame(parsed_results)
    except Exception:
        pass
        
    return pd.DataFrame({"Notice": ["Live Yahoo data stream temporarily busy. Please refresh the page or open a scanner tool via the sidebar."] * 5})

@st.cache_data(ttl=600)
def fetch_live_trending_api(universe_pool):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/trending/US"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        trends = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        
        # If the index pools loaded, filter symbols. Otherwise, pull top raw trending assets.
        if universe_pool:
            valid_symbols = [t["symbol"] for t in trends if t["symbol"] in universe_pool][:10]
        else:
            valid_symbols = [t["symbol"] for t in trends][:10]
            
        if not valid_symbols:
            return pd.DataFrame(columns=["Symbol", "Name", "Last Price ($)", "Change (%)", "Market Cap ($B)"])
            
        quote_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={','.join(valid_symbols)}"
        quote_response = requests.get(quote_url, headers=headers, timeout=5)
        quote_data = quote_response.json()
        quotes = quote_data.get("quoteResponse", {}).get("result", [])
        
        parsed_results = []
        for q in quotes:
            parsed_results.append({
                "Symbol": q.get("symbol"),
                "Name": q.get("shortName", "N/A"),
                "Last Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else "N/A"
            })
        if parsed_results:
            return pd.DataFrame(parsed_results)
    except Exception:
        pass
        
    return pd.DataFrame({"Notice": ["Live Yahoo data stream temporarily busy. Please refresh the page or open a scanner tool via the sidebar."] * 5})


# --- Navigation Sidebar ---
st.sidebar.title("🎯 Alpha Tracker Tools")
st.sidebar.markdown("---")

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if st.sidebar.button("🚀 Mega-Cap ATH Scanner", use_container_width=True):
    st.session_state.current_page = "ATH"

if st.sidebar.button("📈 Nifty 50 Return Ranking", use_container_width=True):
    st.session_state.current_page = "Nifty"

if st.session_state.current_page != "Home":
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Back to Home Landing Page", use_container_width=True):
        st.session_state.current_page = "Home"


# --- Main Dashboard Router ---
if st.session_state.current_page == "Home":
    st.title("🎛️ Investment Analytics Dashboard")
    st.caption("Live asset snapshots generated dynamically from open data registries.")
    
    # Generate the dynamic universe check constraints
    universe_pool = get_dynamic_allowed_universe()
    
    tab1, tab2 = st.tabs(["🔥 Top Gainers", "📊 Trending Tickers"])
    
    with tab1:
        st.subheader("Today's Top Market Gainers")
        with st.spinner("Streaming filtered session gainers..."):
            live_gainers = fetch_live_gainers_api(universe_pool)
            st.dataframe(live_gainers, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("High-Volume Trending Tickers")
        with st.spinner("Streaming filtered trending assets..."):
            live_trending = fetch_live_trending_api(universe_pool)
            st.dataframe(live_trending, use_container_width=True, hide_index=True)

elif st.session_state.current_page == "ATH":
    run_script("ATH_App.py")

elif st.session_state.current_page == "Nifty":
    run_script("Nifty50_Ranking.py")