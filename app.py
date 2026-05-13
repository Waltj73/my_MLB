import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. RELIABLE DATA FETCH
def get_live_vsin():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        return pd.DataFrame(response.json()['data'])
    except:
        return pd.DataFrame()

df_raw = get_live_vsin()

if not df_raw.empty:
    # 3. YOUR EXACT SPREADSHEET MATH
    # Convert text data to numbers
    for col in ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']:
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

    # Math for Payouts & EV (Matches image_2e7fb4.png)
    df_raw['Away_Pay'] = np.where(df_raw['v_ml'] > 0, df_raw['v_ml']/100, 100/abs(df_raw['v_ml']))
    df_raw['Home_Pay'] = np.where(df_raw['h_ml'] > 0, df_raw['h_ml']/100, 100/abs(df_raw['h_ml']))
    
    # Sharp ML (Handle - Bets)
    df_raw['Sharp_ML_Away'] = (df_raw['v_handle_pct'] - df_raw['v_bets_pct']) / 100
    df_raw['Sharp_ML_Home'] = (df_raw['h_handle_pct'] - df_raw['h_bets_pct']) / 100

    # EV Calculation (Assumes 50/50 win rate if no model provided)
    # REPLACE 50.0 with your 'My Win %' if you have the file ready
    df_raw['EV_Away'] = (0.50 * df_raw['Away_Pay'] * 100) - (100 - 50)
    df_raw['EV_Home'] = (0.50 * df_raw['Home_Pay'] * 100) - (100 - 50)

    # 4. THE COMMAND CENTER LAYOUT
    st.title("⚾ MLB Betting Edge: Live VSiN Feed")
    
    # Picks logic based on your green highlights
    df_raw['Pick_Away'] = np.where(df_raw['EV_Away'] > 12, df_raw['away_team'], "")
    df_raw['Pick_Home'] = np.where(df_raw['EV_Home'] > 12, df_raw['home_team'], "")

    # Styled Table
    st.dataframe(
        df_raw[['away_team', 'home_team', 'Sharp_ML_Away', 'Sharp_ML_Home', 'EV_Away', 'EV_Home', 'Pick_Away', 'Pick_Home']]
        .style.background_gradient(subset=['EV_Away', 'EV_Home'], cmap='RdYlGn'),
        use_container_width=True, height=600, hide_index=True
    )
else:
    st.error("Waiting for VSiN to push the live update...")
