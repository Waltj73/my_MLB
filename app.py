import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & SYSTEM BEAT ---
st.set_page_config(page_title="MLB Intelligence Engine", layout="wide")
st_autorefresh(interval=60 * 1000, key="engine_pulse")

# --- 2. THE PROJECTION VAULT ---
# These are your proprietary win probabilities
my_models = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. THE DATA ACQUISITION ---
def fetch_vsin_live():
    # Cache-busting URL to ensure fresh data every minute
    url = f"https://data.vsin.com/betting-splits-data/mlb.json?t={int(time.time())}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        return pd.DataFrame(response.json().get('data', []))
    except:
        return pd.DataFrame()

# --- 4. THE MATCHING ENGINE ---
def bridge_names(live_name):
    """Bridges the gap between VSiN names and your Model names."""
    for team, pct in my_models.items():
        if team.lower() in live_name.lower():
            return pct
    return 50.0

# --- 5. THE EXECUTION ---
raw_data = fetch_vsin_live()

if not raw_data.empty:
    # CLEANING: Standardize the numbers
    cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
    raw_data[cols] = raw_data[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # MATH: EV and Sharp Divergence
    raw_data['My_Win_Pct'] = raw_data['away_team'].apply(bridge_names)
    raw_data['Payout'] = np.where(raw_data['v_ml'] > 0, raw_data['v_ml']/100, 100/abs(raw_data['v_ml']))
    raw_data['EV'] = (raw_data['My_Win_Pct']/100 * raw_data['Payout'] * 100) - (100 - raw_data['My_Win_Pct'])
    raw_data['Sharp_Diff'] = raw_data['v_handle_pct'] - raw_data['v_bets_pct']

    # --- 6. UI: THE COMMAND CENTER ---
    st.title("⚾ MLB Intelligence Command Center")
    st.caption(f"LIVE DATA SYNC | Last Heartbeat: {time.strftime('%H:%M:%S')}")

    # HIGHLIGHT ZONE: Show only the plays with a mathematical edge
    alerts = raw_data[(raw_data['EV'] > 12) | (abs(raw_data['Sharp_Diff']) > 15)].copy()
    
    if not alerts.empty:
        st.subheader("🔥 High-Priority Alerts")
        for _, row in alerts.iterrows():
            with st.expander(f"ALERT: {row['away_team']} @ {row['home_team']}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Expected Value (EV)", f"{row['EV']:.1f}%")
                with col2:
                    st.metric("Sharp Differential", f"{int(row['Sharp_Diff'])}%")
                
                # Dynamic Scout Notes
                if row['EV'] > 12:
                    st.info(f"**SITUATIONAL VALUE**: Your model shows a significant edge relative to the Vegas ML of {row['v_ml']}.")
                if abs(row['Sharp_Diff']) > 15:
                    st.warning(f"**SHARP ACTION**: Professional money is heavy on {row['away_team']} relative to the ticket count.")

    # FULL SLATE TABLE
    st.divider()
    st.subheader("📋 Full Market Overview")
    
    view_df = raw_data[['away_team', 'home_team', 'v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'EV']]
    
    def highlight_ev(val):
        color = '#27ae60' if val > 12 else ('#c0392b' if val < -10 else '')
        return f'background-color: {color}; color: white'

    st.dataframe(view_df.style.applymap(highlight_ev, subset=['EV']), use_container_width=True, hide_index=True)

else:
    st.error("🔄 Connecting to Market Feed... If this takes longer than 10s, check your firewall/VPN.")
