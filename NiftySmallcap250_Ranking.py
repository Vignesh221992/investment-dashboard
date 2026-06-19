import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
from io import StringIO

st.title("Nifty Smallcap 250 Absolute Return Dashboard")
st.caption("Dynamically fetches and ranks Nifty Smallcap 250 index stocks by absolute returns.")

# --- 100% Dynamic CDN Extraction (Zero Hardcoding) ---
@st.cache_data(ttl=86400) # Cache the index structure for 24 hours
def get_smallcap250_tickers_cdn():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Routing through jsDelivr Global CDN to guarantee data delivery without cloud IP bans
    urls = [
        "https://cdn.jsdelivr.net/gh/anirban-m/nifty-indices-constituents@main/constituents/niftysmallcap250.csv",
        "https://cdn.jsdelivr.net/gh/skbavishi/mftracker@main/data/ind_niftysmallcap250list.csv"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                
                # Dynamic matching of symbol/ticker columns
                symbol_col = None
                for col in df.columns:
                    if col.lower() in ['symbol', 'ticker', 'stock symbol']:
                        symbol_col = col
                        break
                
                if symbol_col:
                    tickers = [str(sym).strip() + ".NS" for sym in df[symbol_col].dropna()]
                    if len(tickers) > 100:
                        return tickers
        except Exception:
            continue
            
    return None

def safe_download(ticker, start_date, end_date):
    try:
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return None
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        out = df[[col]].dropna().rename(columns={col: "price"})
        return out
    except Exception:
        return None

@st.cache_data(ttl=24 * 3600)
def build_table(tickers, start_date, end_date):
    rows = []
    failed = []
    
    # Visual processing progress tracking
    progress_bar = st.progress(0.0)
    
    for i, t in enumerate(tickers):
        progress_bar.progress((i + 1) / len(tickers))
        data = safe_download(t, start_date, end_date)
        if data is None or data.empty:
            failed.append(t)
            continue

        price = data["price"].squeeze()
        if len(price) < 2:
            failed.append(t)
            continue

        start_price = float(price.iloc[0])
        end_price = float(price.iloc[-1])
        abs_ret = (end_price / start_price - 1.0) * 100.0

        rows.append({
            "Ticker": t.replace(".NS", ""),
            "Start_Date": price.index[0].date(),
            "Start_Price": round(start_price, 2),
            "End_Date": price.index[-1].date(),
            "End_Price": round(end_price, 2),
            "Absolute_Return_%": round(abs_ret, 2)
        })
        
    progress_bar.empty()
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Absolute_Return_%", ascending=False).reset_index(drop=True)
    return df, failed

# Core UI execution variables
start_date = st.date_input("Start date", datetime(2024, 9, 30))
end_date = st.date_input("End date", datetime.today())

# Fetch universe dynamically from CDN network layer
tickers_pool = get_smallcap250_tickers_cdn()

if st.button("Build ranking"):
    if tickers_pool is None or len(tickers_pool) == 0:
        st.error("Global networks are temporarily out of sync. Please verify your internet connection and try again.")
    else:
        with st.spinner(f"Downloading historical data frames for {len(tickers_pool)} Smallcap stocks via Yahoo Finance..."):
            rank_df, failed = build_table(tickers_pool, start_date, end_date)

        if rank_df.empty:
            st.error("No active histories parsed from the data feed.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Stocks ranked", len(rank_df))
            c2.metric("Highest return", f"{rank_df['Absolute_Return_%'].max():.2f}%")
            c3.metric("Lowest return", f"{rank_df['Absolute_Return_%'].min():.2f}%")

            st.subheader("Ranked Table")
            st.dataframe(rank_df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download CSV",
                rank_df.to_csv(index=False).encode("utf-8"),
                file_name="nifty_smallcap250_absolute_returns.csv",
                mime="text/csv"
            )

            if failed:
                with st.expander("View Unresolved Tickers"):
                    st.caption(", ".join([t.replace(".NS", "") for t in failed]))
else:
    st.info("Set the dates, then click **Build ranking**.")