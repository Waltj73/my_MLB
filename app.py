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

# --- 2. THE POSITIONAL SCRAPER ---
@st.cache_data(ttl=300)
def fetch_and_merge_data():
    scraper = cloudscraper.create_scraper()
    try:
        # SOURCE 1: Games Page (IMPORTHTML Table 1)
        res1 = scraper.get("https://data.vsin.com/mlb/games/", timeout=10)
        df_g = pd.read_html(io.StringIO(res1.text), flavor='lxml')[0]

        # SOURCE 2: Betting Splits (IMPORTHTML Table 1)
        res2 = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB", timeout=10)
        df_s = pd.read_html(io.StringIO(res2.text), flavor='lxml')[0]

        # Process Games by COLUMN POSITION (Safer than names)
        # Column 1: Matchup/Team | Column 5: ML | Column 7: EST Score
        away_g = df_g.iloc[::2].reset_index(drop=True)
        home_g = df_g.iloc[1::2].reset_index(drop=True)
        
        games = pd.DataFrame({
            'Away': away_g.iloc[:, 1].astype(str),
            'Home': home_g.iloc[:, 1].astype(str),
            'Away_ML': pd.to_numeric(away_g.iloc[:, 5], errors='coerce'),
            'Away_Proj': pd.to_numeric(away_g.iloc[:, 7], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_g.iloc[:, 7], errors='coerce')
        })

        # Process Splits by COLUMN POSITION
        # Column 1: Team | Column 9: Handle | Column 10: Bets
        away_s = df_s.iloc[::2].reset_index(drop=True)
        splits = pd.DataFrame({
            'Team_Key': away_s.iloc[:, 1].astype(str),
            'Handle': pd.to_numeric(away_s.iloc[:, 9].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Bets': pd.to_numeric(away_s.iloc[:, 10].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })

        # Clean the names for the merge (Remove city names)
        games['Join_Key'] = games['Away'].str.split().str[-1].str.upper()
        splits['Join_Key'] = splits['Team_Key'].str.split().str[-1].str.upper()

        final = pd.merge(games, splits, on='Join_Key', how='left')
        final['Sharp_Diff'] = final['Handle'] - final['Bets']
        
        return final.dropna(subset=['Away_Proj'])

    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Automated Tactical Dashboard")

df = fetch_and_merge_data()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Live Slate Analysis")
    # Using specific index locations to ensure data shows up
    view = df[['Away', 'Home', 'Away_ML', 'Away_Proj', 'Home_Proj', 'Away_Win_%', 'Away_EV', 'Sharp_Diff']]
    
    st.dataframe(
        view.style.format({
            'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            diff = row['Sharp_Diff'] if pd.notna(row['Sharp_Diff']) else 0
            sharp_team = row['Away'] if diff > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(diff):.0f}% discrepancy).")
            st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
else:
    st.warning("🔄 Data is being processed. If team names are still '0', the website layout may have changed again.")
