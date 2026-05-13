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

# --- 2. INTELLIGENT DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_mlb_data():
    scraper = cloudscraper.create_scraper()
    try:
        # PULL GAMES (EST Projections)
        r1 = scraper.get("https://data.vsin.com/mlb/games/", timeout=10)
        df_g = pd.read_html(io.StringIO(r1.text), flavor='lxml')[0]
        
        # PULL SPLITS (Money/Handle)
        r2 = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB", timeout=10)
        df_s = pd.read_html(io.StringIO(r2.text), flavor='lxml')[0]

        # Helper to find column index by keyword
        find_col = lambda df, k: next((i for i, c in enumerate(df.columns) if k.lower() in str(c).lower()), 1)

        # Process Games (Every 2 rows is a game)
        idx_est = find_col(df_g, 'est')
        idx_ml = find_col(df_g, 'money')
        
        away_g = df_g.iloc[::2].reset_index(drop=True)
        home_g = df_g.iloc[1::2].reset_index(drop=True)
        
        games = pd.DataFrame({
            'Away': away_g.iloc[:, 1].astype(str),
            'Home': home_g.iloc[:, 1].astype(str),
            'Away_Proj': pd.to_numeric(away_g.iloc[:, idx_est], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_g.iloc[:, idx_est], errors='coerce'),
            'Away_ML': pd.to_numeric(away_g.iloc[:, idx_ml], errors='coerce'),
            # Create a Match Key (e.g., "Yankees")
            'Mascot': away_g.iloc[:, 1].astype(str).str.split().str[-1].str.upper()
        })

        # Process Splits
        idx_hnd = find_col(df_s, 'hnd')
        idx_bets = find_col(df_s, 'bet')
        
        split_rows = df_s.iloc[::2].reset_index(drop=True)
        splits = pd.DataFrame({
            'Mascot': split_rows.iloc[:, 1].astype(str).str.split().str[-1].str.upper(),
            'Handle': pd.to_numeric(split_rows.iloc[:, idx_hnd].astype(str).str.replace('%',''), errors='coerce'),
            'Bets': pd.to_numeric(split_rows.iloc[:, idx_bets].astype(str).str.replace('%',''), errors='coerce')
        })

        # Merge and Calculate
        final = pd.merge(games, splits, on='Mascot', how='left')
        final['Sharp_Diff'] = final['Handle'] - final['Bets']
        return final.dropna(subset=['Away_Proj'])

    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI EXECUTION ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Automated Tactical Dashboard")

df = fetch_mlb_data()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Live Slate Analysis")
    cols = ['Away', 'Home', 'Away_ML', 'Away_Proj', 'Home_Proj', 'Away_Win_%', 'Away_EV', 'Sharp_Diff']
    
    st.dataframe(
        df[cols].style.format({
            'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )
else:
    st.info("🔄 Synching VSiN Tables... If names are still missing, refresh in 30 seconds.")
