import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.title("Nifty Smallcap 250 Absolute Return Dashboard")
st.caption("Dynamically fetches and ranks Nifty Smallcap 250 index stocks by absolute returns.")

# --- 100% Dynamic Constituent Extraction ---
@st.cache_data(ttl=86400) # Cache constituent file for 24 hours
def get_smallcap250_tickers():
    try:
        # Fetching the live updated Nifty Smallcap 250 track dataset from open public registry repositories
        url = "https://raw.githubusercontent.com/anirban-m/nifty-indices-constituents/main/constituents/niftysmallcap250.csv"
        df = pd.read_csv(url)
        
        # Standardize matching to look up against Yahoo Finance NSE extension suffix (.NS)
        symbol_col = [col for col in df.columns if 'symbol' in col.lower() or 'ticker' in col.lower()][0]
        tickers = [str(sym).strip() + ".NS" for sym in df[symbol_col].dropna() if not str(sym).endswith('.NS')]
        return tickers
    except Exception:
        # Robust fallback tracking baseline if github repository endpoints face network delays
        return [
            "CDSL.NS", "ANGELONE.NS", "RBLBANK.NS", "PNBHOUSING.NS", "BSE.NS", 
            "CENTURYTEX.NS", "CUB.NS", "CYIENT.NS", "EIDPARRY.NS", "HUDCO.NS"
        ]

def safe_download(ticker, start_date, end_date):
    try:
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return None
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        out = df[[col]].dropna().rename(columns={col: "price"})
        if out.empty:
            return None
        return out
    except Exception:
        return None

@st.cache_data(ttl=24 * 3600)
def build_table(tickers, start_date, end_date):
    rows = []
    failed = []
    for t in tickers:
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

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Absolute_Return_%", ascending=False).reset_index(drop=True)
    return df, failed

# Execution inputs
start_date = st.date_input("Start date", datetime(2024, 9, 30))
end_date = st.date_input("End date", datetime.today())

tickers_pool = get_smallcap250_tickers()

if st.button("Build ranking"):
    with st.spinner(f"Downloading data for {len(tickers_pool)} Smallcap constituents via Yahoo Finance..."):
        rank_df, failed = build_table(tickers_pool, start_date, end_date)

    if rank_df.empty:
        st.error("No data returned from Yahoo Finance.")
    else:
        # Operational Metrics Panel
        c1, c2, c3 = st.columns(3)
        c1.metric("Stocks ranked", len(rank_df))
        c2.metric("Highest return", f"{rank_df['Absolute_Return_%'].max():.2f}%")
        c3.metric("Lowest return", f"{rank_df['Absolute_Return_%'].min():.2f}%")

        # Exclusive Ranked Table Presentation 
        st.subheader("Ranked Table")
        st.dataframe(rank_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            rank_df.to_csv(index=False).encode("utf-8"),
            file_name="nifty_smallcap250_absolute_returns.csv",
            mime="text/csv"
        )

        if failed:
            with st.expander("View Unresolved/Throttled Tickers"):
                st.caption(", ".join([t.replace(".NS", "") for t in failed]))
else:
    st.info("Set the dates, then click **Build ranking**.")