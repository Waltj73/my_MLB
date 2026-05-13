import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import re

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if away_lambda <= 0 or home_lambda <= 0:
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
    if not ml_odds: return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. THE PARSER ---
def parse_vsin_text(text):
    """Extracts Team, ML, and EST Score from pasted text."""
    # Pattern looks for Team Name followed by Odds and EST Score
    pattern = r"([a-zA-Z\s\.]+)\s+([-+]?\d+)\s+([\d\.]+)"
    matches = re.findall(pattern, text)
    data = []
    for i in range(0, len(matches), 2):
        try:
            away = matches[i]
            home = matches[i+1]
            data.append({
                'Away': away[0].strip(),
                'Home': home[0].strip(),
                'Away_ML': float(away[1]),
                'Away_Proj': float(away[2]),
                'Home_Proj': float(home[2])
            })
        except: continue
    return pd.DataFrame(data)

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Tactical Matchup Center")

st.markdown("### 📋 Step 1: Paste Table Data")
raw_input = st.text_area("Copy and paste the table from VSiN here (Ctrl+A, Ctrl+C on the VSiN page)", height=150)

if raw_input:
    df = parse_vsin_text(raw_input)
    
    if not df.empty:
        df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
        df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

        st.header("🏁 Live Slate Analysis")
        st.dataframe(
            df.style.format({'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}'})
            .background_gradient(subset=['Away_EV'], cmap='RdYlGn'),
            use_container_width=True, hide_index=True
        )

        st.divider()
        st.header("🧠 Tactical Scouting Reports")
        for _, row in df.iterrows():
            with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
                st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
                st.metric(f"{row['Away']} Win %", f"{row['Away_Win_%']:.1%}")
                st.metric("Away EV", f"{row['Away_EV']:.2%}")
    else:
        st.error("Could not find team data. Try highlighting the table rows more clearly.")
else:
    st.info("Waiting for data paste to run Poisson engine...")
