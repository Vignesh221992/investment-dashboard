import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO

# Page Setup
st.set_page_config(page_title="Mega-Cap ATH Scanner", layout="wide")
st.title("🚀 Mega-Cap All-Time High Scanner")

# --- SIDEBAR CONFIG ---
st.sidebar.header("Scan Settings")
min_cap = st.sidebar.slider("Min Market Cap ($B)", 100, 1000, 200) * 1_000_000_000
drawdown = st.sidebar.slider("Max % from High", 0.0, 10.0, 1.5, step=0.5)

if st.button("Run Market Scan"):
    with st.spinner("Fetching S&P 500 and analyzing mega-caps... this takes 1-2 mins."):
        
        # Stage 1: Get Universe
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            response = requests.get(url, headers=headers)
            html_data = StringIO(response.text)
            tickers = pd.read_html(html_data)[0]['Symbol'].str.replace('.', '-').tolist()
            
            results = []
            multiplier = 1 - (drawdown / 100)
            
            # Progress bar for the UI
            progress_bar = st.progress(0)
            
            for i, symbol in enumerate(tickers):
                # Update progress
                progress_bar.progress((i + 1) / len(tickers))
                
                try:
                    t = yf.Ticker(symbol)
                    mkt_cap = t.info.get('marketCap', 0)
                    
                    if mkt_cap >= min_cap:
                        hist = t.history(period="max")
                        if hist.empty: continue
                        
                        ath = hist['High'].max()
                        current = t.info.get('regularMarketPrice') or hist['Close'].iloc[-1]
                        
                        if current >= (ath * multiplier):
                            results.append({
                                "Symbol": symbol,
                                "Price": round(current, 2),
                                "ATH": round(ath, 2),
                                "Cap ($T)": round(mkt_cap/1e12, 2),
                                "Distance": f"{((1 - (current/ath)) * 100):.2f}%"
                            })
                except:
                    continue
            
            # Stage 3: Display Results
            if results:
                df = pd.DataFrame(results)
                st.success(f"Found {len(df)} stocks matching your criteria!")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No stocks found within those parameters.")
                
        except Exception as e:
            st.error(f"Error: {e}")