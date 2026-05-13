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

# --- 2. THE POSITION-BASED SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_data():
    try:
        # Load the CSV without headers first to find the starting line
        raw = pd.read_csv(URL, header=None).fillna('')
        
        # Find the first row that actually looks like game data (Home/Away exists)
        start_row = 0
        for i, row in raw.iterrows():
            if any("away" in str(x).lower() for x in row.values):
                start_row = i
                break
        
        # Reload skipping only the trash at the top
        df = pd.read_csv(URL, skiprows=start_row)
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI EXECUTION ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # HELPER: Force column indexing by POSITION (0=A, 1=B, 2=C...)
    # Adjusted based on standard VSiN/MLB sheet layouts
    try:
        # Define positions (Adjust these numbers if your sheet columns shift)
        COL_AWAY = 0    # Col A
        COL_HOME = 1    # Col B
        COL_A_EST = 5   # Col F (Away EST Score)
        COL_H_EST = 6   # Col G (Home EST Score)
        COL_ML = 7      # Col H (MoneyML)
        COL_HND = 12    # Col M (Handle %)
        COL_BET = 13    # Col N (Bets %)

        def clean_num(val):
            s = str(val).replace('%', '').replace(',', '').strip()
            return pd.to_numeric(s, errors='coerce')

        # Calculations
        df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(
            clean_num(x.iloc[COL_A_EST]), 
            clean_num(x.iloc[COL_H_EST])
        ), axis=1)
        
        df['EV'] = df.apply(lambda x: calculate_ev(
            x['Win_Prob'], 
            clean_num(x.iloc[COL_ML])
        ), axis=1)
        
        df['Sharp_Diff'] = clean_num(df.iloc[:, COL_HND]) - clean_num(df.iloc[:, COL_BET])

        # Matchup Selection
        game_list = (df.iloc[:, COL_AWAY].astype(str) + " @ " + df.iloc[:, COL_HOME].astype(str)).tolist()
        selected_game = st.selectbox("🎯 Select Matchup", game_list)
        g = df[(df.iloc[:, COL_AWAY].astype(str) + " @ " + df.iloc[:, COL_HOME].astype(str)) == selected_game].iloc[0]

        # Scouting Report
        st.header(f"📈 Scouting Report: {g.iloc[COL_AWAY]} @ {g.iloc[COL_HOME]}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
        m2.metric("Edge (EV)", f"{g['EV']:.2%}")
        m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

        st.divider()
        st.write(f"📊 **Analytical Logic**: Using implied win probabilities and EV metrics.")
        st.caption("🔄 Live sync active. No manual pasting required.")

    except Exception as e:
        st.error(f"Data Alignment Error: {e}")
        st.info("Check if your spreadsheet columns match the expected positions.")
else:
    st.info("🔄 Awaiting Data... Ensure your 'MLB' tab is populated.")
