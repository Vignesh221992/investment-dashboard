import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.title("Nifty 50 Absolute Return Dashboard")
st.caption("Ranks Nifty 50 stocks by absolute return from Sep 2024 to today.")

TICKERS = [
    "ADANIPORTS.NS","ASIANPAINT.NS","AXISBANK.NS","BAJAJ-AUTO.NS","BAJFINANCE.NS",
    "BAJAJFINSV.NS","BEL.NS","BHARTIARTL.NS","BPCL.NS","BRITANNIA.NS","CIPLA.NS",
    "COALINDIA.NS","DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HCLTECH.NS","HDFCBANK.NS",
    "HEROMOTOCO.NS","HINDALCO.NS","HINDUNILVR.NS","ICICIBANK.NS","INDUSINDBK.NS",
    "INFY.NS","ITC.NS","JIOFIN.NS","JSWSTEEL.NS","KOTAKBANK.NS","LT.NS","M&M.NS",
    "MARUTI.NS","NESTLEIND.NS","NTPC.NS","ONGC.NS","POWERGRID.NS","RELIANCE.NS",
    "SBILIFE.NS","SBIN.NS","SHRIRAMFIN.NS","SUNPHARMA.NS","TATACONSUM.NS",
    "TATAMOTORS.NS","TATASTEEL.NS","TCS.NS","TECHM.NS","TITAN.NS","TRENT.NS",
    "ULTRACEMCO.NS","WIPRO.NS"
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
            "Ticker": t,
            "Start_Date": price.index[0].date(),
            "Start_Price": start_price,
            "End_Date": price.index[-1].date(),
            "End_Price": end_price,
            "Absolute_Return_%": abs_ret
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Absolute_Return_%", ascending=False).reset_index(drop=True)
    return df, failed

start_date = st.date_input(
    "Start date",
    datetime(2024, 9, 30),
    key="nifty50_start_date"
)
end_date = st.date_input(
    "End date",
    datetime.today(),
    key="nifty50_end_date"
)

if st.button("Build ranking", key="nifty50_build_button"):
    with st.spinner("Downloading Yahoo Finance data..."):
        rank_df, failed = build_table(TICKERS, start_date, end_date)

    if rank_df.empty:
        st.error("No data returned from Yahoo Finance.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Stocks ranked", len(rank_df))
        c2.metric("Highest return", f"{rank_df['Absolute_Return_%'].max():.2f}%")
        c3.metric("Lowest return", f"{rank_df['Absolute_Return_%'].min():.2f}%")

        st.subheader("Ranked table")
        st.dataframe(rank_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            rank_df.to_csv(index=False).encode("utf-8"),
            file_name="nifty50_absolute_returns.csv",
            mime="text/csv"
        )

        if failed:
            st.warning("Failed tickers: " + ", ".join(failed))
else:
    st.info("Set the dates, then click **Build ranking**.")