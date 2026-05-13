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

@st.cache_data(ttl=30)
def load_data():
    try:
        raw = pd.read_csv(URL, header=None).fillna('')
        start_row = 0
        for i, row in raw.iterrows():
            if any("away" in str(x).lower() for x in row.values):
                start_row = i
                break
        df = pd.read_csv(URL, skiprows=start_row)
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI & ALIGNMENT ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    # --- DEBUG SECTION: SEE YOUR COLUMN INDEXES ---
    with st.expander("🛠️ Debug: Column Alignment (Open this to check index numbers)"):
        st.write("Match these index numbers to the 'COL_' variables in the code below.")
        debug_df = pd.DataFrame([df.columns], columns=[f"Index {i}" for i in range(len(df.columns))])
        st.table(debug_df)
        st.dataframe(df.head(3))

    # --- ADJUST THESE INDEX NUMBERS BASED ON THE TABLE ABOVE ---
    COL_AWAY = 0    
    COL_HOME = 1    
    COL_A_EST = 5   
    COL_H_EST = 6   
    COL_ML = 7      
    COL_HND = 12    
    COL_BET = 13    

    def clean_num(val):
        s = str(val).replace('%', '').replace(',', '').strip()
        return pd.to_numeric(s, errors='coerce')

    try:
        # Data Processing
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
        st.caption("🔄 Data synced live from your MLB Google Sheet.")

    except Exception as e:
        st.error(f"Alignment Error: {e}")
else:
    st.info("🔄 Awaiting Data...")
