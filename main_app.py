import streamlit as st
import importlib.util
import sys
import pandas as pd
import requests
from io import StringIO

# Page Layout Setup
st.set_page_config(page_title="Alpha Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Helper Function to Dynamically Run Sub-Scripts ---
def run_script(script_path):
    spec = importlib.util.spec_from_file_location("sub_script", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sub_script"] = module
    spec.loader.exec_module(module)

# --- Universe Filter: Dynamically Generate Allowed S&P 500 and NASDAQ Pools ---
@st.cache_data(ttl=86400) # Cache strict universe check for 24 hours to maximize performance
def get_allowed_universe():
    allowed_tickers = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. Fetch S&P 500 Tickers
    try:
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        res = requests.get(sp500_url, headers=headers, timeout=5)
        sp_df = pd.read_html(StringIO(res.text))[0]
        sp_tickers = sp_df['Symbol'].str.replace('.', '-').tolist()
        allowed_tickers.update(sp_tickers)
    except Exception:
        pass # Fallback safety handling if Wikipedia changes structure
        
    # 2. Fetch NASDAQ-100 Tickers
    try:
        nasdaq_wiki = "https://en.wikipedia.org/wiki/Nasdaq-100"
        res_nas = requests.get(nasdaq_wiki, headers=headers, timeout=5)
        nas_df = pd.read_html(StringIO(res_nas.text))[4] # Components table index
        nas_tickers = nas_df['Ticker'].str.replace('.', '-').tolist()
        allowed_tickers.update(nas_tickers)
    except Exception:
        # Core mega-caps fallback padding to guarantee validation coverage
        allowed_tickers.update(["AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST", "NFLX", "ADBE"])
        
    return allowed_tickers


# --- API Streams: Fetch Live Data Directly via Yahoo's Alternate JSON Servers ---
@st.cache_data(ttl=600)
def fetch_live_gainers_api(universe_pool):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
        params = {"scrIds": "day_gainers", "count": 50} # Large count pool to filter against criteria
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        
        parsed_results = []
        for q in quotes:
            symbol = q.get("symbol")
            # Strict Filter Check: Drop if not inside defined index universes
            if symbol not in universe_pool:
                continue
                
            parsed_results.append({
                "Symbol": symbol,
                "Name": q.get("shortName", "N/A"),
                "Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change ($)": round(q.get("regularMarketChange", 0), 2) if q.get("regularMarketChange") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else "N/A",
                "Volume": f"{q.get('regularMarketVolume', 0):,}" if q.get('regularMarketVolume') else "N/A"
            })
            if len(parsed_results) >= 10:
                break
        return pd.DataFrame(parsed_results)
    except Exception as e:
        return pd.DataFrame({"Error": [f"API Connection issue for Gainers: {e}"]})

@st.cache_data(ttl=600)
def fetch_live_trending_api(universe_pool):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/trending/US"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        trends = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        
        # Pre-filter trending stream using index boundaries
        valid_symbols = [t["symbol"] for t in trends if t["symbol"] in universe_pool][:10]
        
        if not valid_symbols:
            return pd.DataFrame(columns=["Symbol", "Name", "Last Price ($)", "Change (%)", "Market Cap ($B)"])
            
        quote_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={','.join(valid_symbols)}"
        quote_response = requests.get(quote_url, headers=headers, timeout=5)
        quote_data = quote_response.json()
        
        # Robust check to gracefully bypass potential quote engine connection limits
        if "quoteResponse" not in quote_data:
            return pd.DataFrame({
                "Symbol": valid_symbols,
                "Status": ["Active Tracking (Details temporarily throttled by Yahoo)"] * len(valid_symbols)
            })
            
        quotes = quote_data["quoteResponse"].get("result", [])
        
        parsed_results = []
        for q in quotes:
            parsed_results.append({
                "Symbol": q.get("symbol"),
                "Name": q.get("shortName", "N/A"),
                "Last Price ($)": round(q.get("regularMarketPrice", 0), 2) if q.get("regularMarketPrice") else "N/A",
                "Change (%)": f"{q.get('regularMarketChangePercent', 0):+.2f}%" if q.get('regularMarketChangePercent') is not None else "N/A",
                "Market Cap ($B)": round(q.get("marketCap", 0) / 1e9, 2) if q.get("marketCap") else "N/A"
            })
        return pd.DataFrame(parsed_results)
    except Exception as e:
        return pd.DataFrame({"Error": [f"API Connection issue for Trending: {e}"]})


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
    st.caption("Live snapshot filtered strictly for S&P 500 and NASDAQ constituents.")
    
    # Initialize the tracking pool
    universe_pool = get_allowed_universe()
    
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