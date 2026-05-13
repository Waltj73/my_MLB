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
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    return np.sum(away_pmf * home_cdf) / (np.sum(away_pmf * home_cdf) + np.sum(home_pmf * away_cdf))

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. THE STACK-AWARE SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        # Using a more aggressive parsing for the EST Score column seen in image.png
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        df = None
        for table in tables:
            if 'EST Score' in table.columns:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # Extract Away (Even rows) and Home (Odd rows)
        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, 1],
            'Home': home_rows.iloc[:, 1],
            'Away_ML': pd.to_numeric(away_rows['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows['MoneyML'], errors='coerce'),
            # Specifically pulling the stacked 3.8 and 5.5 values from image.png
            'Away_Proj': pd.to_numeric(away_rows['EST Score'], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_rows['EST Score'], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away_rows['HandleHND.2'].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows['BetsBET.2'].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away_Proj', 'Home_Proj'])
    except Exception as e:
        st.error(f"Logic Error: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Center", layout="wide")
st.title("⚾ MLB Poisson Matchup Center")

df = fetch_vsin_data()

if not df.empty:
    # Calculate unique Win % based on EST Score (3.8 vs 5.5 etc.)
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Sharp_Diff']
    st.dataframe(
        df[cols].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting: {row['Away']} @ {row['Home']}"):
            st.write(f"📊 **EST Score Projections**: {row['Away']} {row['Away_Proj']} | {row['Home']} {row['Home_Proj']}")
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(row['Sharp_Diff']):.0f}% Discrepancy)")
