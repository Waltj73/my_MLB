import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0:
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
    if pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. MULTI-TABLE SCRAPER ---
@st.cache_data(ttl=300)
def fetch_multi_table_data():
    scraper = cloudscraper.create_scraper()
    all_game_data = []
    
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url, timeout=10)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        for t in tables:
            # Flatten columns to look for markers
            col_list = [str(c).lower() for c in t.columns]
            
            # Check if this table contains game data markers
            if any('est' in c or 'score' in c for c in col_list):
                try:
                    # In these small game tables, Away is row 0, Home is row 1
                    # We find the column index for EST Score and MoneyML dynamically
                    idx_est = next(i for i, c in enumerate(col_list) if 'est' in c)
                    idx_ml = next(i for i, c in enumerate(col_list) if 'money' in c or 'ml' in c)
                    idx_team = next(i for i, c in enumerate(col_list) if 'team' in c or 'matchup' in c or i == 1)
                    
                    game = {
                        'Away': t.iloc[0, idx_team],
                        'Home': t.iloc[1, idx_team],
                        'Away_Proj': pd.to_numeric(t.iloc[0, idx_est], errors='coerce'),
                        'Home_Proj': pd.to_numeric(t.iloc[1, idx_est], errors='coerce'),
                        'Away_ML': pd.to_numeric(t.iloc[0, idx_ml], errors='coerce'),
                        'Home_ML': pd.to_numeric(t.iloc[1, idx_ml], errors='coerce')
                    }
                    all_game_data.append(game)
                except Exception:
                    continue # Skip tables that don't match the format
        
        return pd.DataFrame(all_game_data)
    except Exception as e:
        st.error(f"Error accessing tables: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Multi-Table", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_multi_table_data()

if not df.empty:
    # Calculations
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    st.dataframe(df.style.format({'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}'}), use_container_width=True)

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
            st.write(f"🎯 **Model Edge**: {row['Away_EV']:.1%} EV on the Away side.")
else:
    st.info("Scanning VSiN for individual game tables and EST Scores...")
