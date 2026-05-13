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

# --- 2. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733' # Locks to the MLB tab
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_data():
    try:
        # Step A: Load the sheet and find exactly where the game rows start
        raw = pd.read_csv(URL, header=None).fillna('')
        data_start = 0
        for i, row in raw.iterrows():
            if any(k in str(x).lower() for k in ["away", "home"] for x in row.values):
                data_start = i
                break
        
        # Step B: Reload skipping the trash above your headers
        df = pd.read_csv(URL, skiprows=data_start)
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI & ANALYTICS ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # --- HARD-CODED COLUMN POSITIONS ---
    # These correspond to Columns A, B, C... in your MLB tab
    try:
        POS_AWAY = 0    # Col A
        POS_HOME = 1    # Col B
        POS_A_EST = 5   # Col F (Away EST)
        POS_H_EST = 6   # Col G (Home EST)
        POS_ML = 7      # Col H (MoneyML)
        POS_HND = 12    # Col M (Handle %)
        POS_BET = 13    # Col N (Bets %)

        def clean_val(val):
            s = str(val).replace('%', '').replace(',', '').strip()
            return pd.to_numeric(s, errors='coerce')

        # Calculations
        df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(
            clean_val(x.iloc[POS_A_EST]), 
            clean_val(x.iloc[POS_H_EST])
        ), axis=1)
        
        df['EV'] = df.apply(lambda x: calculate_ev(
            x['Win_Prob'], 
            clean_val(x.iloc[POS_ML])
        ), axis=1)
        
        df['Sharp_Diff'] = clean_val(df.iloc[:, POS_HND]) - clean_val(df.iloc[:, POS_BET])

        # Matchup UI
        matchups = (df.iloc[:, POS_AWAY].astype(str) + " @ " + df.iloc[:, POS_HOME].astype(str)).tolist()
        choice = st.selectbox("🎯 Select Matchup", matchups)
        g = df[(df.iloc[:, POS_AWAY].astype(str) + " @ " + df.iloc[:, POS_HOME].astype(str)) == choice].iloc[0]

        # Final Dashboard
        st.header(f"📈 Scouting Report: {g.iloc[POS_AWAY]} @ {g.iloc[POS_HOME]}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV']:.2%}")
        m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

        st.divider()
        st.write(f"📊 **Data Source**: Using current Poisson Lambdas and Market Odds.")
        st.caption("🔄 Data refreshed from MLB tab. Scalping-ready.")

    except Exception as e:
        st.error(f"Data Alignment Error: {e}")
        st.info("Check if your MLB tab layout matches Columns A through N.")
else:
    st.info("🔄 Connecting to Sheet... Ensure the MLB tab has active data.")
