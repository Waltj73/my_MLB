import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if not away_lambda or not home_lambda or away_lambda == 0: 
        return 0.50
    
    # 0-15 range as per your Excel formula
    scores = np.arange(16)
    
    # Probabilities of exact scores (POISSON.DIST(..., FALSE))
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    # Probabilities of scoring k-1 or fewer (POISSON.DIST(..., TRUE))
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    # Replicating your SUMPRODUCT win logic
    prob_away = np.sum(away_pmf * home_cdf)
    prob_home = np.sum(home_pmf * away_cdf)
    
    return prob_away / (prob_away + prob_home)

# --- 2. DATA PROCESSING ---
@st.cache_data(ttl=300)
def fetch_dynamic_matchups():
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB")
        df = pd.read_html(io.StringIO(response.text), flavor='lxml')[0]
        
        # Merge rows into Matchups
        away = df.iloc[::2].reset_index(drop=True)
        home = df.iloc[1::2].reset_index(drop=True)
        
        matchups = pd.DataFrame({
            'Away': away['MLB - Wednesday, May 13May 13.1'],
            'Home': home['MLB - Wednesday, May 13May 13.1'],
            'Away_ML': pd.to_numeric(away['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home['MoneyML'], errors='coerce'),
            # TARGETING PROJECTED RUNS FROM VSIN FEED
            'Away_Proj': pd.to_numeric(away['ProjectedScore'], errors='coerce'), 
            'Home_Proj': pd.to_numeric(home['ProjectedScore'], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away['HandleHND.2'].str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away['BetsBET.2'].str.extract('(\d+)')[0], errors='coerce')
        })
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups
    except: 
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.title("⚾ MLB Matchup Center: Dynamic Poisson")

df = fetch_dynamic_matchups()

if not df.empty:
    # APPLYING DYNAMIC RUN PROJECTIONS TO POISSON
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    
    # EV Calculation
    def ev(p, ml):
        if pd.isna(ml): return 0
        dec = (ml/100)+1 if ml > 0 else (100/abs(ml))+1
        return (p * (dec-1)) - (1-p)

    df['Away_EV'] = df.apply(lambda x: ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    # TABLE DISPLAY
    st.subheader("🏁 Full Slate Analysis (Dynamic Projections)")
    st.dataframe(
        df[['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Proj', 'Home_Proj', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Sharp_Diff']].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )
