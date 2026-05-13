import streamlit as st
import pandas as pd
import cloudscraper
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge: Live Sharp Analysis", layout="wide")
# Auto-refresh every 5 minutes to catch odds shifts
st_autorefresh(interval=5 * 60 * 1000, key="vsin_update")

# --- 2. DATA SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_splits():
    """Scrapes DraftKings MLB Betting Splits from VSiN."""
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(url)
        # Use 'lxml' (or 'bs4') to parse the table
        tables = pd.read_html(response.text, flavor='bs4')
        
        if not tables:
            return pd.DataFrame()

        df = tables[0]
        
        # Flatten VSiN's multi-row headers (e.g., 'Moneyline' > 'Handle %')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
        
        # --- CLEANING DATA ---
        # Rename VSiN columns to match your existing logic
        # VSiN typically uses columns like 'Matchup', 'Handle_%', 'Bets_%'
        # We find the columns that contain key words to remain flexible
        cols = df.columns.tolist()
        
        # Search for teams and percentages in the raw scrape
        df['Away'] = df.iloc[:, 1].str.split('@').str[0].str.strip()
        df['Home'] = df.iloc[:, 1].str.split('@').str[1].str.strip()
        
        # Identify Handle and Bet % columns (usually indexed by their headers)
        # These typically come in pairs for Away/Home
        # Note: Actual VSiN column names vary by source, but usually contain 'Handle' and 'Bets'
        return df

    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return pd.DataFrame()

# --- 3. ANALYTICS LOGIC ---
def get_detailed_analysis(away, home, sharp_diff):
    reports = {
        ("Angels", "Guardians"): "SHARP ALERT: Massive discrepancy. Targeting Angels bullpen.",
        ("Nationals", "Reds"): "SITUATIONAL EDGE: High winds at GABP. Professional money on Reds ML.",
    }
    default_note = f"MARKET FLOW: No extreme divergence. Sharp Diff: {sharp_diff}%."
    return reports.get((away, home), default_note)

# --- 4. EXECUTION ---
st.title("⚾ MLB Betting Edge: Advanced Sharp Analysis")
st.caption(f"Last sync: {pd.Timestamp.now().strftime('%H:%M:%S')}")

df_raw = fetch_vsin_splits()

if not df_raw.empty:
    # Here we simulate the columns based on typical VSiN structure
    # You may need to adjust these strings based on the 'df_raw' display below
    try:
        # Example Calculation (Adjust column names if VSiN changes them)
        # df_raw['Sharp Diff'] = df_raw['Handle %'] - df_raw['Bets %']
        
        st.header("📋 Live Betting Splits")
        st.dataframe(df_raw, use_container_width=True)
        
        st.divider()
        
        # Summary Section
        st.header("📝 Sharp Scouting Reports")
        # Loop through games to provide notes
        for _, row in df_raw.head(5).iterrows():
            with st.container():
                matchup = row.iloc[1] # Usually the 'Matchup' column
                st.markdown(f"### {matchup}")
                # analysis_text = get_detailed_analysis(row['Away'], row['Home'], 0)
                # st.info(analysis_text)

    except Exception as e:
        st.warning(f"Data mapping error: {e}. Checking raw table structure...")
        st.write(df_raw.columns.tolist())
else:
    st.info("Awaiting live data from VSiN... Ensure 'lxml' is installed.")
