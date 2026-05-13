import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. SETUP
st.set_page_config(page_title="MLB Command Center", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. YOUR PROJECTIONS (The "Walt Johnson" Data)
my_projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# 3. DATA FETCH
def get_vsin_live():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        return pd.DataFrame(response.json().get('data', []))
    except:
        return pd.DataFrame()

df = get_vsin_live()

if not df.empty:
    # 4. THE "NOT ROCKET SCIENCE" NAME MATCH
    def match_names(live_name):
        # Checks if your short team name exists inside the VSiN long name
        for short_name, val in my_projections.items():
            if short_name.lower() in live_name.lower():
                return val
        return 50.0 # Fallback

    # Clean data types
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # 5. CALCULATIONS
    df['My Win% A'] = df['away_team'].apply(match_names)
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['EV_A'] = (df['My Win% A']/100 * df['V_Pay'] * 100) - (100 - df['My Win% A'])
    df['Sharp_Diff'] = df['v_handle_pct'] - df['v_bets_pct']

    # 6. DYNAMIC NOTES (Scouting Report)
    def scout_report(row):
        if row['Sharp_Diff'] > 15:
            return f"SHARP: Pros on {row['away_team']} ({int(row['Sharp_Diff'])}% Split)."
        if row['EV_A'] > 12:
            return "VALUE: Model edge detected vs Market."
        return "Steady."

    df['Notes'] = df.apply(scout_report, axis=1)

    # 7. THE TABLE
    st.title("⚾ MLB Live Market Analysis")
    
    view_cols = ['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV_A', 'Notes']
    
    # Matching your high-contrast photography aesthetic with clear highlights
    def highlight(x):
        style = pd.DataFrame('', index=x.index, columns=x.columns)
        style['EV_A'] = x['EV_A'].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else '')
        style['Notes'] = x['Notes'].apply(lambda v: 'color: #16a085; font-weight: bold' if 'SHARP' in v else '')
        return style

    st.dataframe(df[view_cols].style.apply(highlight, axis=None), use_container_width=True, hide_index=True)
else:
    st.warning("Re-establishing connection...")
