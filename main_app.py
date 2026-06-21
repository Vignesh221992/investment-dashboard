from io import StringIO

import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# 1. Page Layout Setup
st.set_page_config(page_title="Tracker Dashboard", layout="wide", initial_sidebar_state="expanded")

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

COUNTRY_REGION_MAP = {
    "United States": "US",
    "India": "IN",
    "Canada": "CA",
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "Australia": "AU",
    "Japan": "JP"
}

COUNTRY_INDEX_SOURCES = {
    "United States": {
        "type": "csv",
        "url": "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv",
        "symbol_col": "Symbol"
    },
    "India": {
        "type": "csv",
        "url": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
        "symbol_col": "Symbol"
    },
    "Canada": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/S%26P/TSX_60"
    },
    "United Kingdom": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/FTSE_100_Index"
    },
    "Germany": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/DAX"
    },
    "France": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/CAC_40"
    },
    "Australia": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/S%26P/ASX_200"
    },
    "Japan": {
        "type": "wiki",
        "url": "https://en.wikipedia.org/wiki/Nikkei_225"
    }
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

@st.cache_data(ttl=300)
def fetch_market_overview():
    """Fetch lightweight price snapshots for major market indicators."""
    symbols = {
        "S&P 500": "^GSPC",
        "NIFTY 50": "^NSEI",
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Bitcoin": "BTC-USD"
    }

    rows = []
    for label, ticker_symbol in symbols.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info or {}
            hist = ticker.history(period="15d", interval="1d", auto_adjust=False)

            if hist is not None and not hist.empty and len(hist) >= 2:
                close_series = hist["Close"].dropna()
                current_price = info.get("regularMarketPrice") or info.get("currentPrice") or float(close_series.iloc[-1])
                prev_price = float(close_series.iloc[-2]) if len(close_series) >= 2 else float(current_price)
                daily_history = close_series.tail(10)
                chart_values = daily_history.pct_change().fillna(0).mul(100)
            else:
                current_price = info.get("regularMarketPrice") or info.get("currentPrice")
                prev_price = current_price
                daily_history = pd.Series([float(current_price)]).dropna()
                chart_values = pd.Series([0.0], index=daily_history.index)

            if current_price is None or prev_price is None or prev_price <= 0:
                continue

            change_pct = ((float(current_price) - float(prev_price)) / float(prev_price)) * 100
            rows.append({
                "Label": label,
                "Symbol": ticker_symbol,
                "Price": float(current_price),
                "Change (%)": float(change_pct),
                "History": chart_values
            })
        except Exception:
            continue

    return pd.DataFrame(rows)

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


# --- Dynamic market-data fetchers using country-specific universe discovery ---
@st.cache_data(ttl=300)
def fetch_live_gainers_api(region="US", country_label="United States"):
    return fetch_country_snapshot(country_label, mode="gainers")

@st.cache_data(ttl=300)
def fetch_live_trending_api(region="US", country_label="United States"):
    return fetch_country_snapshot(country_label, mode="trending")

@st.cache_data(ttl=86400)
def fetch_dynamic_country_universe(country_label):
    source = COUNTRY_INDEX_SOURCES.get(country_label)
    if not source:
        return []

    try:
        response = requests.get(source["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=20, verify=False)
        response.raise_for_status()
        if response.text.strip():
            csv_df = pd.read_csv(StringIO(response.text))
            symbol_col = source.get("symbol_col")
            if symbol_col in csv_df.columns:
                symbols = csv_df[symbol_col].astype(str).tolist()
                clean_symbols = []
                for s in symbols:
                    s = s.strip()
                    if not s or s == "nan":
                        continue
                    if country_label == "India":
                        clean_symbols.append(f"{s}.NS" if not s.endswith(".NS") else s)
                    else:
                        clean_symbols.append(s.replace('.', '-'))
                return clean_symbols
    except Exception:
        pass

    try:
        tables = pd.read_html(source["url"])
        for table in tables:
            cols = {str(c).lower(): c for c in table.columns}
            if any(k in cols for k in ["symbol", "ticker", "code", "security", "company"]):
                for candidate in ["symbol", "ticker", "code"]:
                    if candidate in cols:
                        symbols = table[cols[candidate]].astype(str).tolist()
                        return [s.strip() for s in symbols if s.strip() and s.strip() != "nan"]
    except Exception:
        pass

    return []

@st.cache_data(ttl=300)
def fetch_country_snapshot(country_label, mode="gainers"):
    symbols = fetch_dynamic_country_universe(country_label)[:60]
    if not symbols:
        return pd.DataFrame(columns=["Country", "Symbol", "Name", "Sector", "Price ($)", "Change ($)", "Change (%)", "Market Cap ($B)"])

    batch = []
    try:
        batch = yf.download(
            symbols,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=30,
        )
    except Exception:
        batch = []

    results = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            name = info.get("shortName") or symbol
            sector = info.get("sector") or resolve_sector(symbol)
            market_cap = info.get("marketCap") or 0
            market_cap_billions = market_cap / 1e9 if market_cap else 0

            if isinstance(batch, pd.DataFrame) and not batch.empty:
                if symbol in batch.columns:
                    hist = batch[symbol]
                elif (symbol, "Close") in batch.columns:
                    hist = batch[(symbol, "Close")]
                else:
                    hist = None
            else:
                hist = None

            if hist is None or hist.empty or len(hist) < 2:
                hist = ticker.history(period="5d", interval="1d", auto_adjust=False)

            if hist is None or hist.empty or len(hist) < 2:
                continue

            close_series = hist["Close"].dropna() if isinstance(hist, pd.DataFrame) and "Close" in hist.columns else pd.Series([hist]).dropna()
            if close_series.empty or len(close_series) < 2:
                continue

            current_price = info.get("regularMarketPrice") or float(close_series.iloc[-1])
            prev_price = float(close_series.iloc[-2])
            if prev_price <= 0:
                continue
            change_pct = ((current_price - prev_price) / prev_price) * 100
            if market_cap_billions <= 0:
                continue
            volume = info.get("regularMarketVolume")
            if volume is None and isinstance(hist, pd.DataFrame) and "Volume" in hist.columns:
                volume = int(hist["Volume"].iloc[-1])

            results.append({
                "Country": country_label,
                "Symbol": symbol,
                "Name": name,
                "Sector": sector,
                "Price ($)": round(current_price, 2),
                "Last Price ($)": round(current_price, 2),
                "Change ($)": round(current_price - prev_price, 2),
                "Change (%)": f"{change_pct:+.2f}%",
                "Market Cap ($B)": round(market_cap_billions, 2),
                "Volume": f"{int(volume):,}" if volume else "N/A"
            })
        except Exception:
            continue

    if mode == "gainers":
        results = sorted(results, key=lambda x: float(x["Change (%)"].replace("%", "")), reverse=True)
    else:
        results = sorted(results, key=lambda x: int(str(x["Volume"]).replace(",", "")) if str(x["Volume"]).isdigit() else 0, reverse=True)

    if mode == "gainers":
        columns = ["Country", "Symbol", "Name", "Sector", "Price ($)", "Change ($)", "Change (%)", "Market Cap ($B)"]
    else:
        columns = ["Country", "Symbol", "Name", "Sector", "Last Price ($)", "Change (%)", "Market Cap ($B)", "Volume"]

    return pd.DataFrame(results[:10], columns=columns) if results else pd.DataFrame(columns=columns)


# --- Navigation Sidebar ---
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


# --- Main Dashboard Router ---
if st.session_state.current_page == "Home":
    market_overview = fetch_market_overview()
    if not market_overview.empty:
        st.subheader("Market Snapshot", divider="rainbow")
        st.markdown(
            """
            <style>
            .snapshot-scroll {
                display: flex;
                overflow-x: auto;
                gap: 12px;
                padding-bottom: 0.5rem;
                scroll-snap-type: x proximity;
            }
            .snapshot-scroll > div {
                flex: 0 0 280px;
                min-width: 280px;
                max-width: 280px;
                scroll-snap-align: start;
            }
            @media (max-width: 768px) {
                .snapshot-scroll > div {
                    flex-basis: 260px;
                    min-width: 260px;
                    max-width: 260px;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="snapshot-scroll">', unsafe_allow_html=True)
        cols = st.columns(len(market_overview))
        for col, row in zip(cols, market_overview.to_dict("records")):
            with col:
                with st.container(border=True):
                    st.caption(row["Label"])
                    st.markdown(
                        f"<div style='font-size:1.35rem; font-weight:600;'>{row['Price']:,.2f}</div>",
                        unsafe_allow_html=True,
                    )
                    delta_color = "#22c55e" if row["Change (%)"] >= 0 else "#ef4444"
                    st.markdown(
                        f"<div style='font-size:0.9rem; color:{delta_color};'>{row['Change (%)']:+.2f}%</div>",
                        unsafe_allow_html=True,
                    )
                    history = row.get("History")
                    chart_data = pd.Series(history).dropna().astype(float) if history is not None else pd.Series(dtype=float)
                    chart_data = chart_data[chart_data.notna()]
                    if len(chart_data) >= 2:
                        chart_frame = chart_data.rename("Daily Move (%)").to_frame()
                        chart_frame.index.name = "Date"
                        st.line_chart(
                            chart_frame,
                            height=90,
                            use_container_width=True,
                        )
                    else:
                        st.write("")
        st.markdown('</div>', unsafe_allow_html=True)

    selected_countries = st.multiselect(
        "Select countries",
        options=list(COUNTRY_REGION_MAP.keys()),
        default=["United States"],
        help="Choose one or more markets to view live top movers and trending stocks."
    )

    if not selected_countries:
        st.warning("Please select at least one country.")
    else:
        tab1, tab2 = st.tabs(["🔥 Top Gainers", "📊 Trending Tickers"])

        with tab1:
            st.subheader("Today's Top Market Gainers")
            with st.spinner("Streaming selected-market gainers..."):
                gainers_frames = []
                for country in selected_countries:
                    region = COUNTRY_REGION_MAP[country]
                    gainers_frames.append(fetch_live_gainers_api(region=region, country_label=country))
                live_gainers = pd.concat(gainers_frames, ignore_index=True) if gainers_frames else pd.DataFrame(columns=[
                    "Country", "Symbol", "Name", "Sector", "Price ($)", "Change ($)", "Change (%)", "Market Cap ($B)"
                ])
                st.dataframe(live_gainers, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("High-Volume Trending Tickers")
            with st.spinner("Streaming selected-market trending stocks..."):
                trending_frames = []
                for country in selected_countries:
                    region = COUNTRY_REGION_MAP[country]
                    trending_frames.append(fetch_live_trending_api(region=region, country_label=country))
                live_trending = pd.concat(trending_frames, ignore_index=True) if trending_frames else pd.DataFrame(columns=[
                    "Country", "Symbol", "Name", "Sector", "Last Price ($)", "Change (%)", "Market Cap ($B)", "Volume"
                ])
                st.dataframe(live_trending, use_container_width=True, hide_index=True)

elif st.session_state.current_page == "ATH":
    run_script("ATH_App.py")

elif st.session_state.current_page == "Nifty":
    run_script("Nifty50_Ranking.py")

elif st.session_state.current_page == "Smallcap250":
    run_script("NiftySmallcap250_Ranking.py")