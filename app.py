import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- 1. THE POISSON ENGINE (Your Precise Excel Math) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if away_lambda <= 0 or home_lambda <= 0:
        return 0.50 
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    # Logic to capture the "Air Gap" pullbacks and win probability
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    p_away = np.sum(away_pmf * home_cdf)
    p_home = np.sum(home_pmf * away_cdf)
    return p_away / (p_away + p_home)

# --- 2. THE DATA BRIDGE ---
@st.cache_data(ttl=60)
def get_vsin_data_bridge():
    """
    Directly fetches the JSON data feed that powers the VSiN tables.
    This bypasses the HTML/Header issues entirely.
    """
    try:
        # Direct API endpoint for the MLB Betting Splits
        url = "https://data.vsin.com/api/splits?sport=MLB&source=DK"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # We extract the specific 'EST Score' and 'Handle' fields you need
        rows = []
        for game in data.get('games', []):
            rows.append({
                'Away': game.get('awayTeam'),
                'Home': game.get('homeTeam'),
                'Away_ML': game.get('awayML'),
                'Away_Proj': float(game.get('awayEstScore', 0)), # The 3.8 value
                'Home_Proj': float(game.get('homeEstScore', 0)), # The 5.5 value
                'Away_Hnd': float(game.get('awayHandle', 0)),
                'Away_Bets': float(game.get('awayBets', 0))
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Bridge Connection Error: {e}")
        return pd.DataFrame()

# --- 3. TACTICAL UI ---
st.set_page_config(page_title="MLB Tactical Bridge", layout="wide")
st.title("⚾ MLB Automated Tactical Dashboard")

df = get_vsin_data_bridge()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Sharp_Diff'] = df['Away_Hnd'] - df['Away_Bets']

    st.header("🏁 Live Slate Analysis")
    st.dataframe(
        df.style.format({'Away_Win_%': '{:.1%}', 'Sharp_Diff': '{:+.0f}%'})
        .background_gradient(subset=['Sharp_Diff'], cmap='RdYlGn'),
        use_container_width=True, hide_index=True
    )
    
    # Individual Tactical Scouting Reports
    for _, row in df.iterrows():
        with st.expander(f"Report: {row['Away']} @ {row['Home']}"):
            st.write(f"📊 **EST Projections**: {row['Away_Proj']} vs {row['Home_Proj']}")
            st.metric("Model Win %", f"{row['Away_Win_%']:.1%}")
else:
    st.info("🔄 Establishing Bridge to VSiN Data Feed...")
