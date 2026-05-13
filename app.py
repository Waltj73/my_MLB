import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. CORE POISSON & EV ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if away_lambda <= 0 or home_lambda <= 0: return 0.50
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
# Replace 'YOUR_SHEET_ID' with the actual ID from your URL
SHEET_ID = 'YOUR_SHEET_ID_HERE' 
SHEET_NAME = 'Sheet1' # Make sure this matches your tab name
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

@st.cache_data(ttl=60) # Refreshes every 60 seconds
def load_sheet_data():
    try:
        df = pd.read_csv(URL)
        # Clean up column names to handle spaces/cases
        df.columns = [c.strip().replace(' ', '_') for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sheet Connection Failed: {e}")
        return pd.DataFrame()

# --- 3. UI & TACTICAL LOGIC ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_sheet_data()

if not df.empty:
    # Use your specific column definitions
    # Expected columns: Away, Home, Away_ML, Away_EST, Home_EST, Handle, Bets
    df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_EST'], x['Home_EST']), axis=1)
    df['EV'] = df.apply(lambda x: calculate_ev(x['Win_Prob'], x['Away_ML']), axis=1)
    df['Sharp_Diff'] = df['Handle'] - df['Bets']

    # Game Selector
    selected_game = st.selectbox("Select Game", df['Away'] + " @ " + df['Home'])
    g = df[(df['Away'] + " @ " + df['Home']) == selected_game].iloc[0]

    # --- TACTICAL REPORT ---
    st.header(f"📈 Tactical Report: {g['Away']} @ {g['Home']}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Poisson Win %", f"{g['Win_Prob']:.1%}")
    m2.metric("Away EV", f"{g['EV']:.2%}")
    m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']}%")

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎯 Model Analysis")
        st.write(f"Based on **{g['Away_EST']}** to **{g['Home_EST']}** lambdas.")
        if g['EV'] > 0.05:
            st.success(f"🎯 **Trade Signal**: Model shows edge on {g['Away']}.")
        
    with c2:
        st.subheader("🐳 Sharp Notes")
        if g['Sharp_Diff'] > 15:
            st.warning(f"🐳 **Institutional Alert**: Sharp money backing {g['Away']}.")
        else:
            st.write("Market remains balanced.")

    st.info("📊 Data synced live from your MLB Spreadsheet.")
else:
    st.info("🔄 Awaiting Sheet Sync... Ensure your Google Sheet ID is correct.")
