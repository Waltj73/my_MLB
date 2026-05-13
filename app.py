import streamlit as st
import pandas as pd
import cloudscraper
import io
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge: Advanced Sharp Analysis", layout="wide")
# Auto-refresh every 5 minutes to keep the data fresh
st_autorefresh(interval=5 * 60 * 1000, key="vsin_update")

# --- 2. DATA SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_splits():
    """Scrapes DraftKings MLB Betting Splits from VSiN."""
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url)
        
        # Wrap the raw HTML text in a StringIO buffer so Pandas treats it as data
        html_data = io.StringIO(response.text)
        
        # Read the table using lxml as the engine
        tables = pd.read_html(html_data, flavor='lxml')
        
        if not tables:
            return pd.DataFrame()

        # Iterate through tables to find the one containing betting data
        # VSiN typically has 'Matchup' or 'Handle' in the headers
        target_df = pd.DataFrame()
        for df in tables:
            if any(term in str(df.columns) for term in ['Matchup', 'Handle', 'Bets', 'DraftKings']):
                target_df = df
                break
        
        if target_df.empty:
            target_df = tables[0] # Fallback to first table if search fails

        # Handle Multi-Index columns (VSiN stacks 'Moneyline' over 'Handle %')
        if isinstance(target_df.columns, pd.MultiIndex):
            target_df.columns = ['_'.join(col).strip() for col in target_df.columns.values]
        
        return target_df

    except Exception as e:
        # We limit the error display to avoid the "HTML wall"
        st.error(f"Scraper Error: {str(e)[:100]}")
        return pd.DataFrame()

# --- 3. ANALYTICS LOGIC ---
def get_detailed_analysis(matchup_name, sharp_diff):
    """Provides automated scouting notes based on market movement."""
    if abs(sharp_diff) > 15:
        return f"🚨 **SHARP ALERT**: Significant {sharp_diff}% divergence between Handle and Bets. Professional money is heavy on one side."
    return f"Market flow remains balanced. Current Sharp Diff: {sharp_diff}%."

# --- 4. EXECUTION ---
st.title("⚾ MLB Betting Edge: Advanced Sharp Analysis")
st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

df = fetch_vsin_splits()

if not df.empty:
    # 1. CLEANING & CALCULATIONS
    # Attempt to find common column names from VSiN's dynamic structure
    # We look for the first column that contains 'Handle' and the first for 'Bets'
    handle_col = next((c for c in df.columns if 'Handle' in c and '%' in c), None)
    bets_col = next((c for c in df.columns if 'Bets' in c and '%' in c), None)
    matchup_col = next((c for c in df.columns if 'Matchup' in c or 'Game' in c), df.columns[1])

    if handle_col and bets_col:
        # Clean string percentages to floats
        for col in [handle_col, bets_col]:
            df[col] = df[col].astype(str).str.replace('%', '').astype(float)
        
        df['Sharp Diff'] = df[handle_col] - df[bets_col]
    
    # --- UI LAYOUT ---
    st.header("📋 Live Betting Splits")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # Section 2: Top Moves
    st.header("🎯 Significant Sharp Moves")
    if 'Sharp Diff' in df.columns:
        top_moves = df[abs(df['Sharp Diff']) > 10].copy()
        
        if not top_moves.empty:
            for _, row in top_moves.iterrows():
                with st.expander(f"View Analysis: {row[matchup_col]}"):
                    st.info(get_detailed_analysis(row[matchup_col], row['Sharp Diff']))
        else:
            st.write("No major sharp discrepancies detected at this hour.")
    
else:
    st.warning("Awaiting live data. If this persists, verify your 'requirements.txt' includes lxml and html5lib.")
