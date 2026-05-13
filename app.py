import streamlit as st
import pandas as pd
import numpy as np
import cloudscraper
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# --- 2. YOUR MODEL PROJECTIONS ---
# These are your personal win % probabilities
my_projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. THE STEALTH DATA FETCH ---
def fetch_vsin_stealth():
    # Cloudscraper bypasses the "Establishing connection" hang
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    url = f"https://data.vsin.com/betting-splits-data/mlb.json?t={int(time.time())}"
    try:
        response = scraper.get(url, timeout=10)
        return pd.DataFrame(response.json().get('data', []))
    except:
        return pd.DataFrame()

# --- 4. EXECUTION ---
df = fetch_vsin_stealth()

if not df.empty:
    # THE NAME BRIDGE: Matches "NY Yankees" to "Yankees" automatically
    def match_team(name):
        for short, val in my_projections.items():
            if short.lower() in name.lower():
                return val
        return 50.0

    # Clean numbers for math
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # WALT JOHNSON MATH: EV & Sharp Diff
    df['My Win% A'] = df['away_team'].apply(match_team)
    df['V_Payout'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['EV_Away'] = (df['My Win% A']/100 * df['V_Payout'] * 100) - (100 - df['My Win% A'])
    df['Sharp_Diff'] = df['v_handle_pct'] - df['v_bets_pct']

    # DYNAMIC NOTES (The Scouting Report)
    def get_notes(row):
        if row['Sharp_Diff'] > 15: return f"🔥 SHARP: {int(row['Sharp_Diff'])}% Money Gap"
        if row['EV_Away'] > 12: return "🎯 VALUE: Edge detected"
        return "Steady"
    df['Live_Notes'] = df.apply(get_notes, axis=1)

    # --- 5. THE TABLE ---
    st.title("⚾ MLB Live Command Center")
    st.caption(f"Status: Live Syncing | Last Update: {time.strftime('%H:%M:%S')}")

    view_cols = ['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV_Away', 'Live_Notes']
    
    def color_ev(val):
        color = '#27ae60' if val > 12 else ('#c0392b' if val < -10 else '')
        return f'background-color: {color}; color: white'

    st.dataframe(df[view_cols].style.applymap(color_ev, subset=['EV_Away']), use_container_width=True, hide_index=True)
else:
    st.error("🔄 Connection Blocked. Attempting Stealth Re-sync...")
