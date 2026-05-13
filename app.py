import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge: Live Sync", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# --- 2. YOUR PROJECTIONS ---
# These must remain static so your model logic stays intact
projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. LIVE DATA ENGINE ---
@st.cache_data(ttl=120)
def fetch_live_vsin():
    """Fetches live market data and maps it to your projections."""
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        live_data = response.json().get('data', [])
        df = pd.DataFrame(live_data)
        
        # CLEANING: Convert strings to numbers so math doesn't break
        num_cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except:
        return pd.DataFrame()

# --- 4. EXECUTION ---
df = fetch_live_vsin()

if not df.empty:
    # THE NAME BRIDGE: Matches "NY Yankees" to "Yankees" automatically
    def get_my_win_pct(team_name):
        for short_name, pct in projections.items():
            if short_name.lower() in team_name.lower():
                return pct
        return 50.0 # Fallback to prevent app crash

    df['My Win% Away'] = df['away_team'].apply(get_my_win_pct)
    df['My Win% Home'] = 100 - df['My Win% Away']

    # MATH: Payouts & EV (Matches your spreadsheet logic)
    df['V_Pay'] = np.where(df['v_ml'] > 0, df['v_ml']/100, 100/abs(df['v_ml']))
    df['H_Pay'] = np.where(df['h_ml'] > 0, df['h_ml']/100, 100/abs(df['h_ml']))
    
    df['EV Away'] = (df['My Win% Away']/100 * df['V_Pay'] * 100) - (100 - df['My Win% Away'])
    df['EV Home'] = (df['My Win% Home']/100 * df['H_Pay'] * 100) - (100 - df['My Win% Home'])
    df['Sharp Diff'] = df['v_handle_pct'] - df['v_bets_pct']

    # --- UI LAYOUT ---
    st.title("⚾ MLB Betting Edge: Live Market Analysis")
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # Section 1: Full Slate Table
    st.header("📋 Live Market Data")
    view_df = df[['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'Sharp Diff', 'EV Away', 'EV Home']]
    
    # HIGHLIGHTING: Matches your green/red sheet aesthetic
    def highlight_ev(val):
        color = '#2ecc71' if val > 12 else ('#e74c3c' if val < -10 else '')
        return f'background-color: {color}'

    st.dataframe(view_df.style.applymap(highlight_ev, subset=['EV Away', 'EV Home']), use_container_width=True, hide_index=True)

    # Section 2: Dynamic Scouting Reports
    st.divider()
    st.header("📝 Sharp Scouting Reports")
    top_plays = df[(abs(df['Sharp Diff']) > 15) | (df['EV Away'] > 12) | (df['EV Home'] > 12)].copy()
    
    for _, row in top_plays.iterrows():
        with st.container():
            st.subheader(f"{row['away_team']} @ {row['home_team']}")
            if abs(row['Sharp Diff']) > 15:
                st.info(f"**SHARP ALERT**: {int(row['Sharp_Diff'])}% discrepancy between Handle and Bets. Professional money is moving on this game.")
            if row['EV Away'] > 12 or row['EV Home'] > 12:
                st.success(f"**VALUE PLAY**: Your model shows a significant EV edge relative to the Vegas moneyline.")
            st.markdown("---")
else:
    st.warning("🔄 Re-syncing with VSiN servers... Please wait.")
