import streamlit as st
import pandas as pd
import numpy as np
import cloudscraper
from streamlit_autorefresh import st_autorefresh

# 1. SETUP
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=120 * 1000, key="vsin_update")

# 2. THE FIXED FETCH (Bypassing the error in image_2e710d.png)
def fetch_vsin_data():
    # Use cloudscraper to handle security challenges
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # This is the primary JSON data endpoint for MLB splits
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    
    try:
        response = scraper.get(url, timeout=10)
        # Verify we got a successful response (200 OK)
        if response.status_code == 200:
            raw_json = response.json()
            return pd.DataFrame(raw_json['data'])
        else:
            st.error(f"VSiN Server returned status code: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        # This handles the specific JSON error seen in image_2e710d.png
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# 3. YOUR MATH & LOGIC
raw_df = fetch_vsin_data()

if not raw_df.empty:
    df = raw_df.copy()
    
    # Safely calculate payouts using numpy to avoid ValueErrors
    df['Away_Payout'] = np.where(df['v_ml'].astype(float) > 0, df['v_ml'].astype(float)/100, 100/abs(df['v_ml'].astype(float)))
    df['Home_Payout'] = np.where(df['h_ml'].astype(float) > 0, df['h_ml'].astype(float)/100, 100/abs(df['h_ml'].astype(float)))
    
    # Sharp ML calculation (Handle - Bets)
    df['Sharps_ML_Away'] = (df['v_handle_pct'].astype(float) - df['v_bets_pct'].astype(float)) / 100
    df['Sharps_ML_Home'] = (df['h_handle_pct'].astype(float) - df['h_bets_pct'].astype(float)) / 100

    # Insert your specific model win percentages here
    # Example placeholder based on your sheet's logic:
    df['My_Win_Away'] = 50.0  # Replace with your actual model logic
    df['My_Win_Home'] = 100 - df['My_Win_Away']

    # EV Calculation matching your spreadsheet
    df['EV_Away'] = (df['My_Win_Away']/100 * df['Away_Payout'] * 100) - (100 - df['My_Win_Away'])
    df['EV_Home'] = (df['My_Win_Home']/100 * df['Home_Payout'] * 100) - (100 - df['My_Win_Home'])

    # Picks (Threshold matching your green highlights)
    df['Pick_Away'] = np.where(df['EV_Away'] > 12, df['away_team'], "")
    df['Pick_Home'] = np.where(df['EV_Home'] > 12, df['home_team'], "")

    # 4. HORIZONTAL LAYOUT
    st.title("⚾ MLB Betting Edge: Live Command Center")
    
    def highlight_sheet(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        for col in ['EV_Away', 'EV_Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 10 else ('background-color: #f1948a; color: black' if v < -10 else ''))
        for col in ['Pick_Away', 'Pick_Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #16a085; color: white; font-weight: bold' if v != "" else '')
        return style_df

    st.dataframe(
        df[['away_team', 'home_team', 'Sharps_ML_Away', 'Sharps_ML_Home', 'EV_Away', 'EV_Home', 'Pick_Away', 'Pick_Home']]
        .style.apply(highlight_sheet, axis=None),
        use_container_width=True,
        height=600,
        hide_index=True
    )
else:
    st.warning("Re-establishing connection to live feed...")
