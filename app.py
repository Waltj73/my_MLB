import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# 1. SETUP & REFRESH
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_sync")

# 2. DATA FETCH (Pulling the actual VSiN feed)
def get_vsin_data():
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return pd.DataFrame(response.json()['data'])
    except:
        return pd.DataFrame()

df = get_vsin_data()

if not df.empty:
    # 3. DATA CLEANING
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # 4. THE WALT JOHNSON MATH
    # Sharp ML (Handle - Bets)
    df['Sharp_ML_A'] = (df['v_handle_pct'] - df['v_bets_pct']) / 100
    df['Sharp_ML_H'] = (df['h_handle_pct'] - df['h_bets_pct']) / 100

    # EV Calculation (Assuming your 12% threshold for green highlights)
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['H_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))
    
    # Replace 50.0 with your 'My Win %' as needed
    df['EV_A'] = (0.50 * df['V_Pay'] * 100) - 50
    df['EV_H'] = (0.50 * df['H_Pay'] * 100) - 50

    # Dynamic Note Logic: This generates notes based on REAL data
    def generate_note(row):
        if abs(row['Sharp_ML_A']) > 0.15:
            return f"SHARP ALERT: Heavy {row['away_team']} money flow (+{int(row['Sharp_ML_A']*100)}% Diff)."
        elif row['EV_A'] > 12 or row['EV_H'] > 12:
            return "VALUE PLAY: EV threshold met. Market mispricing detected."
        return "Standard Market Flow."

    df['Live_Scouting_Report'] = df.apply(generate_note, axis=1)

    # 5. THE TABLE VIEW (Full Width)
    st.title("⚾ MLB Betting Dashboard")
    
    display_df = df[['away_team', 'home_team', 'v_ml', 'h_ml', 'Sharp_ML_A', 'Sharp_ML_H', 'EV_A', 'EV_H', 'Live_Scouting_Report']]

    def highlight_sheet(x):
        style_df = pd.DataFrame('', index=x.index, columns=x.columns)
        for c in ['EV_A', 'EV_H']:
            style_df[c] = x[c].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 12 else '')
        style_df['Live_Scouting_Report'] = x['Live_Scouting_Report'].apply(lambda v: 'font-weight: bold; color: #16a085' if 'SHARP' in v else '')
        return style_df

    st.dataframe(
        display_df.style.apply(highlight_sheet, axis=None),
        use_container_width=True,
        height=600,
        hide_index=True
    )
else:
    st.error("Failed to connect to live VSiN feed. Retrying...")
