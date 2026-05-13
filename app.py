import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. CORE MATH ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0 or home_lambda <= 0:
        return 0.50
    scores = np.arange(16)
    away_pmf, home_pmf = poisson.pmf(scores, away_lambda), poisson.pmf(scores, home_lambda)
    away_cdf, home_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda), poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    p_away = np.sum(away_pmf * home_cdf)
    p_home = np.sum(home_pmf * away_cdf)
    return p_away / (p_away + p_home)

def calculate_ev(win_prob, ml_odds):
    if not ml_odds or pd.isna(ml_odds) or ml_odds == 0: return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. DATA SYNC (MLB TAB) ---
# Your specific Google Sheet ID and MLB tab GID
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_data():
    try:
        # Load raw to find data start
        raw = pd.read_csv(URL, header=None).fillna('')
        start_row = 0
        for i, row in raw.iterrows():
            if any("away" in str(x).lower() for x in row.values):
                start_row = i
                break
        df = pd.read_csv(URL, skiprows=start_row)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI & ANALYTICAL EXECUTION ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # --- HARD-WIRED COLUMN MAPPING ---
    # We find columns by keywords to stay flexible if they shift slightly
    def find_idx(keywords):
        for i, col in enumerate(df.columns):
            if any(k.lower() in col.lower() for k in keywords): return i
        return None

    # Targeting your specific columns for Poisson/EV/Sharp analysis
    IDX_AWAY = find_idx(['away team', 'away'])
    IDX_HOME = find_idx(['home team', 'home'])
    IDX_A_EST = find_idx(['away est', 'est score']) # Column F
    IDX_H_EST = find_idx(['home est', 'est score']) # Column G
    IDX_ML = find_idx(['moneyml', 'money ml'])      # Column H
    IDX_HND = find_idx(['handlehnd.2', 'handle'])   # Column M
    IDX_BET = find_idx(['betsbet.2', 'bets'])       # Column N

    def clean_num(val):
        return pd.to_numeric(str(val).replace('%', '').replace(',', '').strip(), errors='coerce')

    try:
        # Core Analytics
        df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(
            clean_num(x.iloc[IDX_A_EST]), 
            clean_num(x.iloc[IDX_H_EST])
        ), axis=1)
        
        df['EV'] = df.apply(lambda x: calculate_ev(
            x['Win_Prob'], 
            clean_num(x.iloc[IDX_ML])
        ), axis=1)
        
        df['Sharp_Diff'] = clean_num(df.iloc[:, IDX_HND]) - clean_num(df.iloc[:, IDX_BET])

        # Selector UI
        game_list = (df.iloc[:, IDX_AWAY].astype(str) + " @ " + df.iloc[:, IDX_HOME].astype(str)).tolist()
        selected_game = st.selectbox("🎯 Select Matchup", game_list)
        g = df[(df.iloc[:, IDX_AWAY].astype(str) + " @ " + df.iloc[:, IDX_HOME].astype(str)) == selected_game].iloc[0]

        # Final Report
        st.header(f"📈 Scouting Report: {g.iloc[IDX_AWAY]} @ {g.iloc[IDX_HOME]}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
        col2.metric("Edge (EV)", f"{g['EV']:.2%}")
        col3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

        st.divider()
        st.caption("🔄 Live sync: Update your Google Sheet and this dashboard refreshes in 30s.")

    except Exception as e:
        st.error(f"Alignment Failure: {e}. Check that Away/Home columns exist in your MLB tab.")
else:
    st.info("🔄 Awaiting Data Sync...")
