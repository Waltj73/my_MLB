import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. CORE MATH ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0 or home_lambda <= 0:
        return 0.50
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    p_away = np.sum(away_pmf * home_cdf)
    p_home = np.sum(home_pmf * away_cdf)
    return p_away / (p_away + p_home)

def calculate_ev(win_prob, ml_odds):
    if not ml_odds or pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. LIVE GOOGLE SHEETS CONNECTION ---
# Using your exact Sheet ID and GID for the MLB tab
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30) # High-frequency refresh for live trading
def load_live_slate():
    try:
        df = pd.read_csv(URL)
        # Clean column headers
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Interrupted: {e}")
        return pd.DataFrame()

# --- 3. DASHBOARD EXECUTION ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_live_slate()

if not df.empty:
    # Calculation Layer
    # Based on your sheet, targeting 'EST Score', 'MoneyML', 'HandleHND.2', and 'BetsBET.2'
    df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(x.get('Away EST', 0), x.get('Home EST', 0)), axis=1)
    df['EV'] = df.apply(lambda x: calculate_ev(x['Win_Prob'], x.get('MoneyML', 0)), axis=1)
    
    # Handle % cleaning
    df['H_Pct'] = pd.to_numeric(df.get('HandleHND.2', '0').astype(str).str.replace('%',''), errors='coerce')
    df['B_Pct'] = pd.to_numeric(df.get('BetsBET.2', '0').astype(str).str.replace('%',''), errors='coerce')
    df['Sharp_Diff'] = df['H_Pct'] - df['B_Pct']

    # Game Selection
    game_list = (df['Away'] + " @ " + df['Home']).tolist()
    selected_game = st.selectbox("🎯 Select Matchup for Scouting Report", game_list)
    g = df[(df['Away'] + " @ " + df['Home']) == selected_game].iloc[0]

    # --- TACTICAL SCOUTING REPORT ---
    st.header(f"📈 Scouting Report: {g['Away']} @ {g['Home']}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
    col2.metric("Edge (EV)", f"{g['EV']:.2%}")
    col3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

    st.divider()
    
    left, right = st.columns(2)
    with left:
        st.subheader("🎯 Tactical Notes")
        st.write(f"Projections: **{g.get('Away EST')}** (Away) vs **{g.get('Home EST')}** (Home)")
        if g['EV'] > 0.08:
            st.success(f"**Value Alert**: High positive EV detected on {g['Away']}.")
        elif g['EV'] < -0.08:
            st.warning(f"**Overvalued**: Market is pricing {g['Away']} significantly higher than the Poisson model.")

    with right:
        st.subheader("🐳 Institutional Flow")
        if abs(g['Sharp_Diff']) > 15:
            st.info(f"**Sharp Move**: A {g['Sharp_Diff']}% gap exists between Money and Tickets.")
        else:
            st.write("Market sentiment is currently balanced.")

    st.caption("🔄 Data is synced directly from your MLB Google Sheet every 30 seconds.")

else:
    st.info("🔄 Connecting to Google Sheet... Ensure the sheet is shared as 'Anyone with the link can view'.")
