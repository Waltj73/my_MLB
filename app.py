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
    if not ml_odds or pd.isna(ml_odds) or ml_odds == 0: return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. THE HARD-WIRED SYNC ENGINE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733' # Direct GID for the MLB Tab
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_live_data():
    try:
        # Load the CSV, forcing all data to strings to prevent 'float' errors
        df = pd.read_csv(URL, dtype=str).fillna('0')
        # Clean up column headers by removing any extra spaces or quotes
        df.columns = [str(c).strip().replace('"', '') for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Critical Connection Error: {e}")
        return pd.DataFrame()

# --- 3. UI & ANALYTICS ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_live_data()

if not df.empty:
    # Helper: Convert data to numbers safely
    def to_num(val):
        try:
            return pd.to_numeric(str(val).replace('%', '').replace(',', '').strip(), errors='coerce')
        except:
            return 0.0

    # DYNAMIC COLUMN SEARCH (Finds your specific Poisson/EV metrics)
    # We look for the exact names from your spreadsheet ledger
    cols = df.columns.tolist()
    
    def get_c(keywords):
        for c in cols:
            if any(k.lower() in c.lower() for k in keywords): return c
        return None

    # Targeting the specific variables you use for scalping and technical analysis
    c_away = get_c(['away'])
    c_home = get_c(['home'])
    c_a_est = get_c(['away est', 'a_est']) # Lambda A
    c_h_est = get_c(['home est', 'h_est']) # Lambda B
    c_ml = get_c(['moneyml', 'ml'])        # Market Odds
    c_hnd = get_c(['handlehnd.2', 'handle'])
    c_bet = get_c(['betsbet.2', 'bets'])

    if c_away and c_home:
        # 4. CALCULATION LAYER
        # We perform calculations on the whole dataframe at once for speed
        df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(to_num(x[c_a_est]), to_num(x[c_h_est])), axis=1)
        df['EV'] = df.apply(lambda x: calculate_ev(x['Win_Prob'], to_num(x[c_ml])), axis=1)
        df['Sharp_Diff'] = df.apply(lambda x: to_num(x[c_hnd]) - to_num(x[c_bet]), axis=1)

        # 5. UI SELECTOR
        matchups = (df[c_away] + " @ " + df[c_home]).tolist()
        choice = st.selectbox("🎯 Select Matchup", matchups)
        g = df[(df[c_away] + " @ " + df[c_home]) == choice].iloc[0]

        # --- TACTICAL SCOUTING REPORT ---
        st.header(f"📈 Scouting Report: {g[c_away]} @ {g[c_home]}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV']:.2%}")
        m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

        st.divider()
        st.write(f"📊 **Projections**: {g[c_a_est]} (Away) vs {g[c_h_est]} (Home)")
        
        if g['EV'] > 0.08:
            st.success("**Value Detected**: Model shows significant edge over market ML.")
        
        st.caption("🔄 Live sync active from Google Sheet tab [MLB]. Refreshes every 30s.")
    else:
        st.error("Header Mismatch: Ensure the MLB tab has columns named 'Away' and 'Home'.")
else:
    st.info("🔄 Connecting to Sheet...")
