import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_heartbeat")

# --- 2. YOUR PROJECTIONS (The "Walt Johnson" Projections) ---
projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. LIVE DATA ENGINE (Cache-Busting) ---
def fetch_vsin_live():
    # Adding a timestamp (?t=) prevents the server from sending old cached data
    url = f"https://data.vsin.com/betting-splits-data/mlb.json?t={int(time.time())}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://vsin.com/'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return pd.DataFrame(response.json().get('data', []))
    except:
        return pd.DataFrame()

# --- 4. DATA CLEANING & MATCHING ---
df = fetch_vsin_live()

if not df.empty:
    # THE NAME BRIDGE: Automatically matches "NY Yankees" to "Yankees"
    def match_team(live_name):
        for short, val in projections.items():
            if short.lower() in live_name.lower():
                return val
        return 50.0 # Safety default

    # Numeric conversion to prevent crashes
    num_cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # CALCULATIONS
    df['My Win% A'] = df['away_team'].apply(match_team)
    df['V_Payout'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['EV_Away'] = (df['My Win% A']/100 * df['V_Payout'] * 100) - (100 - df['My Win% A'])
    df['Sharp_Diff'] = df['v_handle_pct'] - df['v_bets_pct']

    # NOTES (Dynamic Scouting Report)
    def scout_report(row):
        if row['Sharp_Diff'] > 15: return f"SHARP: {int(row['Sharp_Diff'])}% money gap detected."
        if row['EV_Away'] > 12: return "VALUE: High EV relative to market."
        return "Stable flow."

    df['Live_Notes'] = df.apply(scout_report, axis=1)

    # --- 5. UI LAYOUT ---
    st.title("⚾ MLB Live Command Center")
    st.write(f"**Status:** Connected | **Last Sync:** {time.strftime('%H:%M:%S')}")

    view_cols = ['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV_Away', 'Live_Notes']
    
    # Spreadsheet-style Highlighting
    def highlight_ev(val):
        color = '#27ae60' if val > 12 else ('#c0392b' if val < -10 else '')
        return f'background-color: {color}; color: white'

    st.dataframe(df[view_cols].style.applymap(highlight_ev, subset=['EV_Away']), 
                 use_container_width=True, hide_index=True)
else:
    st.error("🔄 Sync Issue: VSiN feed is currently timing out. Retrying...")
