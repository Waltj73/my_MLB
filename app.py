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
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=10)
def load_data():
    try:
        # Load the rawest form of the data possible
        df = pd.read_csv(URL).fillna(0)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # This is the "Safety Valve" - if the math fails, we can see the data below
    with st.expander("🔍 View Raw Data Sync (Verify columns here)"):
        st.dataframe(df)

    # 4. FLEXIBLE COLUMN TARGETING
    # We look for keywords. If 'Away EST' is in column 5 or column 10, it doesn't matter.
    def get_col(names):
        for c in df.columns:
            if any(n.lower() in c.lower() for n in names): return c
        return None

    c_away = get_col(['away'])
    c_home = get_col(['home'])
    c_a_est = get_col(['away est', 'a_est'])
    c_h_est = get_col(['home est', 'h_est'])
    c_ml = get_col(['money', 'ml'])
    c_hnd = get_col(['handle'])
    c_bet = get_col(['bets'])

    # 5. EXECUTION
    try:
        def to_f(v):
            return pd.to_numeric(str(v).replace('%','').strip(), errors='coerce')

        df['WP'] = df.apply(lambda x: calculate_poisson_win_prob(to_f(x[c_a_est]), to_f(x[c_h_est])), axis=1)
        df['EV_Calc'] = df.apply(lambda x: calculate_ev(x['WP'], to_f(x[c_ml])), axis=1)
        
        # UI
        games = (df[c_away].astype(str) + " @ " + df[c_home].astype(str)).tolist()
        sel = st.selectbox("🎯 Select Matchup", games)
        g = df[(df[c_away].astype(str) + " @ " + df[c_home].astype(str)) == sel].iloc[0]

        # Final Dashboard metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['WP']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV_Calc']:.2%}")
        
        diff = to_f(g[c_hnd]) - to_f(g[c_bet])
        m3.metric("Sharp Diff", f"{diff:.0f}%")
        
        st.divider()
        st.write(f"**Live Scouting**: {g[c_away]} vs {g[c_home]}")
        st.caption("🔄 Data auto-refreshed from MLB tab.")

    except Exception as e:
        st.warning(f"Formatting Issue: {e}")
        st.info("The app is connected, but the column names in your sheet might need a quick check.")
else:
    st.info("🔄 Connecting...")
