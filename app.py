import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. YOUR PROJECTIONS (The "Walt Johnson" Data)
# These remain static while the Vegas lines and Splits update live
my_win_projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# 3. ROBUST DATA FETCH
def get_vsin_data():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json().get('data', [])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

df = get_vsin_data()

if not df.empty:
    # 4. THE NAME BRIDGE (Prevents the "Broken" Crashes)
    def find_my_win_pct(team_name):
        for key in my_win_projections:
            if key.lower() in team_name.lower():
                return my_win_projections[key]
        return 50.0 # Default if no match found

    # Convert all numeric columns to float immediately
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # 5. CALCULATIONS (Vectorized for Speed)
    df['My Win% Away'] = df['away_team'].apply(find_my_win_pct)
    df['My Win% Home'] = 100 - df['My Win% Away']
    
    # Sharp ML Logic (Handle % - Bets %)
    df['Sharp ML Away'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharp ML Home'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # Payouts
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['H_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))

    # EV Calculation (Matches Column V & W in your sheet)
    df['EV Away'] = (df['My Win% Away']/100 * df['V_Pay'] * 100) - (100 - df['My Win% Away'])
    df['EV Home'] = (df['My Win% Home']/100 * df['H_Pay'] * 100) - (100 - df['My Win% Home'])

    # Picks (Threshold for Green Highlights)
    df['Pick Away'] = np.where(df['EV Away'] > 12, df['away_team'], "")
    df['Pick Home'] = np.where(df['EV Home'] > 12, df['home_team'], "")

    # 6. THE TABLE VIEW
    st.title("⚾ MLB Live Command Center")
    st.caption(f"Status: Live Syncing VSiN | Last Update: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # Selecting the exact horizontal layout you established
    final_view = df[['away_team', 'home_team', 'v_ml', 'h_ml', 'Sharp ML Away', 'Sharp ML Home', 'EV Away', 'EV Home', 'Pick Away', 'Pick Home']]
    
    def style_output(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        # Apply your spreadsheet coloring
        for c in ['EV Away', 'EV Home']:
            style_df[c] = x[c].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else '')
        for p in ['Pick Away', 'Pick Home']:
            style_df[p] = x[p].apply(lambda v: 'background-color: #16a085; color: white' if v != "" else '')
        return style_df

    st.dataframe(
        final_view.style.apply(style_output, axis=None),
        use_container_width=True,
        height=650,
        hide_index=True
    )
else:
    st.warning("Establishing connection to live data feed...")
