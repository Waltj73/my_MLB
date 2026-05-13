import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. CORE MATH ENGINE (Poisson & EV) ---
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

# --- 2. DATA SYNC ENGINE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733' # Target: MLB Tab
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_live_data():
    try:
        # Load the CSV directly from the MLB tab
        df = pd.read_csv(URL)
        # Clean headers: remove spaces and hidden characters
        df.columns = [str(c).strip().replace('"', '') for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Interrupted: {e}")
        return pd.DataFrame()

# --- 3. UI & TACTICAL ANALYSIS ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_live_data()

if not df.empty:
    # --- DYNAMIC COLUMN MAPPING ---
    def find_col(keywords):
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords): return col
        return None

    # Mapping your specific analytics columns
    c_away = find_col(['away'])
    c_home = find_col(['home'])
    c_a_est = find_col(['away est', 'a_est']) # Lambda A
    c_h_est = find_col(['home est', 'h_est']) # Lambda B
    c_ml = find_col(['money', 'ml'])          # Market ML
    c_hnd = find_col(['handle'])              # Handle %
    c_bet = find_col(['bets'])                # Bets %

    def to_num(val):
        return pd.to_numeric(str(val).replace('%','').replace(',','').strip(), errors='coerce')

    try:
        # Core Calculations
        df['WP'] = df.apply(lambda x: calculate_poisson_win_prob(to_num(x[c_a_est]), to_num(x[c_h_est])), axis=1)
        df['EV_Calc'] = df.apply(lambda x: calculate_ev(x['WP'], to_num(x[c_ml])), axis=1)
        df['Sharp_Diff'] = to_num(df[c_hnd]) - to_num(df[c_bet])

        # Selector UI
        game_list = (df[c_away].astype(str) + " @ " + df[c_home].astype(str)).tolist()
        selected_game = st.selectbox("🎯 Select Matchup", game_list)
        g = df[(df[c_away].astype(str) + " @ " + df[c_home].astype(str)) == selected_game].iloc[0]

        # Final Dashboard metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['WP']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV_Calc']:.2%}")
        m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

        st.divider()
        st.write(f"📊 **Analytical Logic**: Using implied win probabilities and EV metrics.")
        st.caption("🔄 Data synced live from MLB tab. No manual pasting required.")

    except Exception as e:
        st.warning(f"Column Alignment Error: {e}")
        st.info("Check your 'MLB' tab headers. Ensure 'Away', 'Home', 'Away EST', 'Home EST', and 'MoneyML' are present.")
        # Debugger: Show exactly what the app sees
        st.write("Headers found in your sheet:", list(df.columns))
else:
    st.info("🔄 Connecting to Live Sheet... Ensure the MLB tab is populated.")
