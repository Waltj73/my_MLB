import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP ---
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="sync_heartbeat")

# --- 2. THE PROJECTIONS ---
projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. THE STEALTH FETCH ---
def get_vsin_live():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    # Using full headers to prevent the 'Connecting...' hang
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://vsin.com/'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return pd.DataFrame(response.json().get('data', []))
    except:
        pass
    return pd.DataFrame()

# --- 4. EXECUTION ---
raw_df = get_vsin_live()

if not raw_df.empty:
    # THE NAME MATCH: Links "NY Yankees" -> "Yankees" automatically
    def find_win_pct(live_name):
        for short_name, val in projections.items():
            if short_name.lower() in live_name.lower():
                return val
        return 50.0

    # Type-safe cleanup
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    raw_df[cols] = raw_df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # CALCULATIONS
    raw_df['My_Win_A'] = raw_df['away_team'].apply(find_win_pct)
    raw_df['V_Payout'] = np.where(raw_df['v_ml'] > 0, raw_df['v_ml']/100, 100/abs(raw_df['v_ml']))
    raw_df['EV_Away'] = (raw_df['My_Win_A']/100 * raw_df['V_Payout'] * 100) - (100 - raw_df['My_Win_A'])
    raw_df['Sharp_Diff'] = raw_df['v_handle_pct'] - raw_df['v_bets_pct']

    # NOTES (Scouting Report)
    def scout_report(row):
        if row['Sharp_Diff'] > 15: return f"SHARP: {int(row['Sharp_Diff'])}% money gap."
        if row['EV_Away'] > 12: return "VALUE: Edge detected."
        return "Steady"

    raw_df['Notes'] = raw_df.apply(scout_report, axis=1)

    # --- 5. THE TABLE ---
    st.title("⚾ MLB Live Command Center")
    st.caption(f"Heartbeat: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    display_cols = ['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV_Away', 'Notes']
    
    def highlight(x):
        style = pd.DataFrame('', index=x.index, columns=x.columns)
        style['EV_Away'] = x['EV_Away'].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else '')
        style['Notes'] = x['Notes'].apply(lambda v: 'font-weight: bold; color: #16a085' if 'SHARP' in v else '')
        return style

    st.dataframe(raw_df[display_cols].style.apply(highlight, axis=None), use_container_width=True, hide_index=True)
else:
    # Fail-safe display so you're never staring at a blank screen
    st.error("Live Feed Blocked. Retrying with stealth headers...")
    st.info("Ensure you are not running behind a VPN that VSiN might block.")
