import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. MATH ENGINE ---
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
        # Load exactly as it sits in the CSV
        df = pd.read_csv(URL)
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # --- DIRECT INDEX MAPPING ---
    # Change these numbers ONLY if your sheet columns move
    # 0 = Col A, 1 = Col B, 5 = Col F, etc.
    try:
        def to_f(v):
            return pd.to_numeric(str(v).replace('%','').strip(), errors='coerce')

        # Core Metrics for your betting model
        df['WP'] = df.apply(lambda x: calculate_poisson_win_prob(to_f(x.iloc[5]), to_f(x.iloc[6])), axis=1) # Col F & G
        df['EV'] = df.apply(lambda x: calculate_ev(x['WP'], to_f(x.iloc[7])), axis=1) # Col H (ML)
        
        # Market Sentiment
        df['Sharp'] = df.apply(lambda x: to_f(x.iloc[12]) - to_f(x.iloc[13]), axis=1) # Col M & N

        # Matchup Selector
        games = (df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str)).tolist()
        sel = st.selectbox("🎯 Select Matchup", games)
        g = df[(df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str)) == sel].iloc[0]

        # Scouting Report Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['WP']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV']:.2%}")
        m3.metric("Sharp Diff", f"{g['Sharp']:.0f}%")

        st.divider()
        st.write(f"📈 **Live Scouting**: {g.iloc[0]} vs {g.iloc[1]}")
        st.caption("🔄 Data auto-refreshed from MLB tab.")

    except Exception as e:
        st.warning("⚠️ Column Alignment Failure. Displaying raw data for verification:")
        st.dataframe(df.head(5))
else:
    st.info("🔄 Connecting to Sheet...")
