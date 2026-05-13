import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Calculates win probability using the Poisson distribution (0-15 range)."""
    if away_lambda <= 0 or home_lambda <= 0:
        return 0.50 
    
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    """Calculates Expected Value based on Win % and Vegas Moneyline."""
    if not ml_odds: return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. UI DASHBOARD ---
st.set_page_config(page_title="MLB Poisson Dashboard", layout="wide")
st.title("⚾ Stable MLB Matchup Dashboard")

# Manual Input Section for reliability
st.sidebar.header("Matchup Input")
away_team = st.sidebar.text_input("Away Team", "Nationals")
home_team = st.sidebar.text_input("Home Team", "Reds")

col1, col2 = st.sidebar.columns(2)
away_ml = col1.number_input(f"{away_team} ML", value=+120)
home_ml = col2.number_input(f"{home_team} ML", value=-140)

# The EST Scores you identified in your screenshot
st.sidebar.subheader("EST Scores (Lambdas)")
away_est = st.sidebar.number_input(f"{away_team} EST Score", value=3.8, step=0.1)
home_est = st.sidebar.number_input(f"{home_team} EST Score", value=5.5, step=0.1)

# Sharp Data Entry
away_hnd = st.sidebar.slider("Away Handle %", 0, 100, 45)
away_bets = st.sidebar.slider("Away Bets %", 0, 100, 30)
sharp_diff = away_hnd - away_bets

# --- 3. CALCULATIONS & DISPLAY ---
away_win_p = calculate_poisson_win_prob(away_est, home_est)
home_win_p = 1 - away_win_p

away_ev = calculate_ev(away_win_p, away_ml)
home_ev = calculate_ev(home_win_p, home_ml)

# Result Table
st.header(f"🏁 Analysis: {away_team} @ {home_team}")
results_df = pd.DataFrame({
    "Team": [away_team, home_team],
    "ML": [away_ml, home_ml],
    "EST Score": [away_est, home_est],
    "Win %": [away_win_p, home_win_p],
    "EV": [away_ev, home_ev]
})

st.table(results_df.style.format({
    "Win %": "{:.1%}",
    "EV": "{:.2%}"
}))

# --- 4. TACTICAL SCOUTING REPORT ---
st.divider()
st.header("🧠 Tactical Scouting Report")

c1, c2 = st.columns(2)

with c1:
    st.subheader("Sharp Sentiment")
    sharp_target = away_team if sharp_diff > 10 else home_team if sharp_diff < -10 else "Neutral"
    st.write(f"🐳 **Sharp Target**: {sharp_target}")
    st.write(f"Discrepancy: {abs(sharp_diff)}%")

with c2:
    st.subheader("Model Conviction")
    if away_ev > 0.05:
        st.write(f"🎯 **Model Edge**: Strong value on {away_team}.")
    elif home_ev > 0.05:
        st.write(f"🎯 **Model Edge**: Strong value on {home_team}.")
    else:
        st.write("⚖️ **Market Balanced**: No significant Poisson edge found.")

st.info(f"Report generated using EST Scores: {away_est} vs {home_est}")
