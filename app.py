import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. LIVE SYNC CONFIG
st.set_page_config(page_title="MLB Betting Command Center", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update") # Refresh every 2 mins

# 2. DATA ACQUISITION
def fetch_vsin_live():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        return pd.DataFrame(response.json().get('data', []))
    except:
        return pd.DataFrame()

df = fetch_vsin_live()

if not df.empty:
    # 3. NUMERIC CLEANUP
    num_cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # 4. TRADING LOGIC & EV CALCULATIONS
    # Sharp Delta (Handle% - Bets%)
    df['Sharp_Delta_A'] = (df['v_handle_pct'] - df['v_bets_pct'])
    
    # Calculate Payouts & EV (Using a baseline 50% Win Rate for live demo)
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['EV_Away'] = (0.50 * df['V_Pay'] * 100) - 50

    # 5. DYNAMIC NOTE GENERATOR (The "Scouting Report")
    def get_detailed_note(row):
        notes = []
        if abs(row['Sharp_Delta_A']) >= 15:
            notes.append(f"⚠️ SHARP MOVE: {int(row['Sharp_Delta_A'])}% Money/Ticket Gap.")
        if row['EV_Away'] > 12:
            notes.append("🎯 VALUE: High Expected Value detected vs Market.")
        if row['v_handle_pct'] > 80:
            notes.append("📢 PUBLIC LOAD: Extreme lopsided handle.")
        
        return " | ".join(notes) if notes else "Steady Market Flow"

    df['Live_Scouting_Report'] = df.apply(get_detailed_note, axis=1)

    # 6. HORIZONTAL COMMAND VIEW
    st.title("⚾ MLB Live Market Analysis")
    
    # Selecting the core columns for your dashboard
    view_cols = ['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV_Away', 'Live_Scouting_Report']
    
    # Apply Spreadsheet-style formatting
    def highlight_plays(x):
        style = pd.DataFrame('', index=x.index, columns=x.columns)
        # Highlight high EV in green
        style['EV_Away'] = x['EV_Away'].apply(lambda v: 'background-color: #27ae60; color: white' if v > 12 else '')
        # Bold the notes for Sharp moves
        style['Live_Scouting_Report'] = x['Live_Scouting_Report'].apply(lambda v: 'color: #e67e22; font-weight: bold' if 'SHARP' in v else '')
        return style

    st.dataframe(
        df[view_cols].style.apply(highlight_plays, axis=None),
        use_container_width=True,
        height=600,
        hide_index=True
    )
else:
    st.error("Failed to connect to VSiN Live Data. Check connection.")
