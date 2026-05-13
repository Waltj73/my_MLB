import streamlit as st
import pandas as pd
import cloudscraper
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=5 * 60 * 1000, key="vsin_update") # 5 min refresh

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    
    # URL 1: Betting Splits (Handle/Bets)
    # VSiN often uses an internal API. We try to pull the JSON directly.
    splits_url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    
    try:
        # Note: In a real environment, you'd target their JSON endpoint: 
        # https://vsin.com/api/get-splits/... 
        # For now, we use pandas to read the tables directly from the HTML
        response = scraper.get(splits_url)
        tables = pd.read_html(response.text)
        
        # Usually, the first table on this page contains the splits
        df = tables[0]
        
        # --- DATA CLEANING ---
        # VSiN tables often have multi-index headers or non-standard names.
        # We need to map them to your existing logic.
        df.columns = [
            'Time', 'Matchup', 'ML_Away', 'ML_Home', 
            'Bets_Away', 'Handle_Away', 'Bets_Home', 'Handle_Home'
        ]
        
        # Basic parsing of the 'Matchup' column to get Away/Home names
        df[['Away', 'Home']] = df['Matchup'].str.split(' @ ', expand=True)
        
        # Convert percentages (like '60%') to numbers (60.0)
        for col in ['Bets_Away', 'Handle_Away']:
            df[col] = df[col].str.replace('%', '').astype(float)
            
        return df

    except Exception as e:
        st.error(f"Error fetching live data: {e}")
        # Return an empty dataframe so the app doesn't crash
        return pd.DataFrame()

# --- 3. THE "MODEL" LOGIC ---
def calculate_metrics(df):
    if df.empty: return df
    
    # Example logic for Sharp Diff
    df['Sharp Diff'] = df['Handle_Away'] - df['Bets_Away']
    
    # Since VSiN doesn't give "My Win %", we set a default or use your previous logic
    # In a real setup, you'd merge this with your Poisson/Python script results
    df['My Win% Away'] = 50.0 
    
    return df

# --- 4. EXECUTION ---
raw_df = fetch_vsin_data()
df = calculate_metrics(raw_df)

if not df.empty:
    st.title("⚾ MLB Live Sharp Moves")
    st.caption(f"Data sourced from DraftKings via VSiN | Updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")
    
    st.header("📊 Current Splits")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Could not load live data. The VSiN site may be blocking the request or the table structure has changed.")
