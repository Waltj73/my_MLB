import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. LAYOUT & REFRESH
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="sync")

# 2. FAIL-SAFE DATA FETCH
def fetch_live_data():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        # Simplified request to avoid "Expecting value" errors
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json().get('data', [])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

df = fetch_live_data()

if not df.empty:
    # CLEANING: Ensure all numeric columns are actually numbers
    num_cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. YOUR EXACT SHEET LOGIC
    # Sharp ML (Column H & N)
    df['Sharps ML Away'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharps ML Home'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # Payouts (Handling +/- Moneyline)
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['H_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))

    # EV Calculation (Matches Column V & W)
    # Note: Using 50% as a placeholder; plug in your "My Win %" here
    df['EV Away'] = (0.50 * df['V_Pay'] * 100) - 50
    df['EV Home'] = (0.50 * df['H_Pay'] * 100) - 50

    # Picks (Column Y & Z)
    df['Pick Away'] = np.where(df['EV Away'] > 12, df['away_team'], "")
    df['Pick Home'] = np.where(df['EV Home'] > 12, df['home_team'], "")

    # 4. HORIZONTAL TABLE VIEW
    st.title("⚾ MLB Betting Dashboard")
    
    # Selecting columns in the order of your spreadsheet
    final_df = df[['away_team', 'home_team', 'v_ml', 'h_ml', 'Sharps ML Away', 'Sharps ML Home', 'EV Away', 'EV Home', 'Pick Away', 'Pick Home']]
    
    # Renaming for a cleaner look
    final_df.columns = ['Away', 'Home', 'V_ML', 'H_ML', 'Sharp_A', 'Sharp_H', 'EV_A', 'EV_H', 'Pick_A', 'Pick_H']

    # Custom Styling to match image_2e7fb4.png
    def style_table(val):
        if isinstance(val, float) and val > 12: return 'background-color: #2ecc71; color: black'
        if val and isinstance(val, str) and val != "": return 'background-color: #16a085; color: white'
        return ''

    st.dataframe(final_df.style.applymap(style_table), use_container_width=True, height=600, hide_index=True)

else:
    st.warning("🔄 Connecting to VSiN Live Feed... Check connection if this persists.")
