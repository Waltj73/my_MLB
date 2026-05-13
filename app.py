import streamlit as st
import pandas as pd
import requests

# Set page layout
st.set_page_config(page_title="MLB Live Edge Dashboard", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=300)  # Refreshes every 5 minutes
def get_vsin_data():
    # 1. Fetch Game/Odds Data
    games_url = "https://data.vsin.com/mlb/games/"
    # 2. Fetch Betting Splits (DK source)
    splits_url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    
    # In a real script, we fetch the JSON from these endpoints
    # Note: These URLs often require specific headers to act like a browser
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # This is a simplified structure of how we process the VSiN JSON
        # You will need to inspect the Network tab in your browser to get the exact JSON keys
        games_res = requests.get(games_url, headers=headers).json()
        splits_res = requests.get(splits_url, headers=headers).json()
        
        # Logic to merge games and splits into one DataFrame goes here
        # For this example, we build the structure based on your screenshot
        df = pd.DataFrame(games_res['data']) 
        return df
    except:
        st.error("Connection to VSiN failed. Using cached/simulated data structure.")
        return pd.DataFrame()

# --- CALCULATIONS ---
def calculate_ev(row):
    # This replicates your spreadsheet math: (Win% * Payout) - Loss%
    # Adjust variables based on your specific 'My Odds' model
    try:
        my_win_prob = row['My Win%'] / 100
        vegas_payout = 100 / abs(row['Vegas ML']) if row['Vegas ML'] < 0 else row['Vegas ML'] / 100
        ev = (my_win_prob * vegas_payout) - (1 - my_win_prob)
        return round(ev * 100, 2)
    except:
        return 0

# --- USER INTERFACE ---
st.title("⚾ MLB Betting Edge: Live VSiN Feed")

data = get_vsin_data()

if not data.empty:
    # 1. Apply your custom "My Odds" Logic
    # (Example: using a simple 5% adjustment or your own proprietary formula)
    data['EV'] = data.apply(calculate_ev, axis=1)

    # 2. Replicate the Spreadsheet View
    st.subheader("Vegas Odds vs. Sharp Splits")
    
    # Define columns to match your 'image_3aaaf5.png'
    cols_to_show = [
        'Away Team', 'Home Team', 'Vegas Odds', 'Handle %', 'Bets %', 'EV'
    ]
    
    # Add conditional formatting for the "Sharp" and "EV" columns
    def highlight_edge(s):
        return ['background-color: #2ecc71' if v > 10 else '' for v in s]

    styled_df = data[cols_to_show].style.apply(highlight_edge, subset=['EV'])
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # 3. Bottom Section: Specific "Picks" based on your logic
    st.divider()
    st.subheader("🎯 Automated Top Picks")
    top_picks = data[data['EV'] > 15] # Only show games with > 15% Edge
    st.table(top_picks[['Away Team', 'Home Team', 'EV']])

else:
    st.warning("Awaiting live data feed from VSiN...")

# 4. Auto-refresh the page
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60000, key="datarefresh") # Refresh every 60 seconds
