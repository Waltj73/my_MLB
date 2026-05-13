import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. PAGE CONFIG & REFRESH
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. RELIABLE VSIN DATA FETCH
def get_vsin_data():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return pd.DataFrame(response.json()['data'])
    except:
        pass
    return pd.DataFrame()

# 3. PROCESSING
df = get_vsin_data()

if not df.empty:
    # Ensure numeric types for calculations
    cols_to_fix = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[cols_to_fix] = df[cols_to_fix].apply(pd.to_numeric, errors='coerce')

    # --- WALT JOHNSON SHEET MATH ---
    # Sharps ML (Handle % - Bets %)
    df['Sharps ML Away'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharps ML Home'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # Payouts & EV Logic (Matches Columns V & W)
    df['Away_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['Home_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))
    
    # Placeholder for 'My Win %' - replace 50.0 with your model's column
    df['EV Away'] = (50.0/100 * df['Away_Pay'] * 100) - (100 - 50.0)
    df['EV Home'] = (50.0/100 * df['Home_Pay'] * 100) - (100 - 50.0)

    # Picks (Threshold for Green Highlights in image_2e7fb4.png)
    df['Pick Away'] = np.where(df['EV Away'] > 12, df['away_team'], "")
    df['Pick Home'] = np.where(df['EV Home'] > 12, df['home_team'], "")

    # --- THE TABLE VIEW ---
    st.title("⚾ MLB Betting Dashboard")
    
    # Selection of columns that mirror image_2e7fb4.png precisely
    display_cols = [
        'away_team', 'home_team', 'v_ml', 'h_ml', 
        'Sharps ML Away', 'Sharps ML Home', 
        'EV Away', 'EV Home', 
        'Pick Away', 'Pick Home'
    ]

    # Styling for that Spreadsheet Look
    def apply_sheet_style(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        # EV Shading
        for c in ['EV Away', 'EV Home']:
            style_df[c] = x[c].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else '')
        # Pick Shading
        for p in ['Pick Away', 'Pick Home']:
            style_df[p] = x[p].apply(lambda v: 'background-color: #16a085; color: white' if v != "" else '')
        return style_df

    st.dataframe(
        df[display_cols].style.apply(apply_sheet_style, axis=None),
        use_container_width=True,
        height=650,
        hide_index=True
    )
else:
    st.warning("Connecting to VSiN Live Feed...")
