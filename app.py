import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. PAGE SETUP
st.set_page_config(page_title="MLB Betting Edge: Live Sync", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. LIVE FETCH
def get_live_vsin():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return pd.DataFrame(response.json()['data'])
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

raw_df = get_live_vsin()

if not raw_df.empty:
    # 3. DATA CLEANING (Ensuring math doesn't break)
    # Mapping VSiN column names to your preferred logic
    df = raw_df[['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']].copy()
    
    # Convert all betting numbers to floats so math works
    for col in ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. YOUR EXACT MATH
    # Sharp ML (Handle - Bets)
    df['Sharp ML Away'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharp ML Home'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # Payouts for EV Calculation
    df['Away_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['Home_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))
    
    # EV Logic (Using 50% as a baseline; replace with your 'My Win %' as needed)
    df['EV Away'] = (0.50 * df['Away_Pay'] * 100) - 50
    df['EV Home'] = (0.50 * df['Home_Pay'] * 100) - 50

    # Picks (Shading logic for EV > 12)
    df['Pick Away'] = np.where(df['EV Away'] > 12, df['away_team'], "")
    df['Pick Home'] = np.where(df['EV Home'] > 12, df['home_team'], "")

    # 5. THE TABLE VIEW (Full Width & Scannable)
    st.title("⚾ MLB Betting Dashboard: Live Feed")
    st.caption(f"App Heartbeat: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # Formatting to match image_2e7fb4.png
    display_df = df[['away_team', 'home_team', 'v_ml', 'h_ml', 'Sharp ML Away', 'Sharp ML Home', 'EV Away', 'EV Home', 'Pick Away', 'Pick Home']]
    
    def highlight_sheet(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        # Apply your Green/Red logic from the spreadsheet
        for col in ['EV Away', 'EV Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else ('background-color: #f1948a; color: black' if v < -10 else ''))
        # Bold the Picks
        for col in ['Pick Away', 'Pick Home']:
            style_df[col] = x[col].apply(lambda v: 'background-color: #16a085; color: white; font-weight: bold' if v != "" else '')
        return style_df

    st.dataframe(
        display_df.style.apply(highlight_sheet, axis=None),
        use_container_width=True,
        height=600,
        hide_index=True
    )
else:
    st.warning("🔄 Re-establishing connection to VSiN servers...")
