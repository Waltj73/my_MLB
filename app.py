import streamlit as st
import pandas as pd
import numpy as np
import cloudscraper
from streamlit_autorefresh import st_autorefresh

# 1. PAGE SETUP
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=120 * 1000, key="vsin_update") # Refresh every 2 mins

# 2. THE LIVE FETCH (The logic to update with VSiN)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    # Official VSiN/DraftKings split data endpoint
    url = "https://data.vsin.com/betting-splits-data/mlb.json" 
    try:
        response = scraper.get(url)
        # Pulling the core betting data
        raw_data = response.json()['data']
        df = pd.DataFrame(raw_data)
        return df
    except Exception as e:
        st.error(f"Error connecting to VSiN: {e}")
        return pd.DataFrame()

# 3. PROCESSING & MATH
raw_df = fetch_vsin_data()

if not raw_df.empty:
    # Rename VSiN columns to match your sheet's naming
    # Note: Adjust column names below based on exact VSiN JSON keys (e.g., 'handle_pct_away')
    df = raw_df.copy()
    
    # --- YOUR SHEET LOGIC ---
    # Handle the Moneyline Math safely with numpy
    df['Away_Payout'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['Home_Payout'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))
    
    # Implied Odds
    df['Vegas_Win_Away'] = 100 / (df['Away_Payout'] + 1)
    df['Vegas_Win_Home'] = 100 / (df['Home_Payout'] + 1)

    # Sharp ML (Column H & N in your sheet)
    df['Sharps_ML_Away'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharps_ML_Home'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # My Win % (This pulls from your pre-defined projections)
    # You can link this to your Google Sheet or a local CSV for live projections
    # df['My_Win_Away'] = pd.read_csv('your_projections.csv')['win_pct']
    
    # EV Calculation (Matches Column V & W in image_2e7fb4.png)
    df['EV_Away'] = (df['My_Win_Away']/100 * df['Away_Payout'] * 100) - (100 - df['My_Win_Away'])
    df['EV_Home'] = (df['My_Win_Home']/100 * df['Home_Payout'] * 100) - (100 - df['My_Win_Home'])

    # Picks (Column Y & Z)
    df['Pick_Away'] = np.where(df['EV_Away'] > 12, df['away_team'], "")
    df['Pick_Home'] = np.where(df['EV_Home'] > 12, df['home_team'], "")

    # 4. THE HORIZONTAL LAYOUT (Matching image_2e7fb4.png)
    st.title("⚾ MLB Betting Edge: Live VSiN Command Center")
    
    def highlight_sheet(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        # EV/Diff Shading
        for col in ['EV_Away', 'EV_Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 10 else ('background-color: #f1948a; color: black' if v < -10 else ''))
        # Picks Shading
        for col in ['Pick_Away', 'Pick_Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #16a085; color: white; font-weight: bold' if v != "" else '')
        return style_df

    # Display the final, dense table
    st.dataframe(
        df[['away_team', 'home_team', 'Sharps_ML_Away', 'Sharps_ML_Home', 'EV_Away', 'EV_Home', 'Pick_Away', 'Pick_Home']]
        .style.apply(highlight_sheet, axis=None),
        use_container_width=True,
        height=700,
        hide_index=True
    )
else:
    st.warning("Awaiting live feed from VSiN...")
