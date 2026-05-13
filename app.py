import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. THE POISSON ENGINE (Core Logic) ---
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
    # Implied win percentages rather than estimated runs
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. USER INPUTS (The Manual Bridge) ---
st.set_page_config(page_title="MLB Tactical Engine", layout="wide")
st.title("⚾ MLB Tactical Matchup Center")

with st.sidebar:
    st.header("📋 Live Game Entry")
    away_t = st.text_input("Away Team", "Away")
    home_t = st.text_input("Home Team", "Home")
    
    c1, c2 = st.columns(2)
    a_ml = c1.number_input(f"{away_t} MoneyML", value=139) # From image_2067d9.png
    h_ml = c2.number_input(f"{home_t} MoneyML", value=-160)
    
    st.subheader("📊 EST Scores (Lambdas)")
    a_est = st.number_input(f"{away_t} EST Score", value=3.8, step=0.1) #
    h_est = st.number_input(f"{home_t} EST Score", value=5.5, step=0.1)
    
    st.subheader("🐳 Sharp Sentiment")
    hnd = st.slider("Handle % (Money)", 0, 100, 75)
    bets = st.slider("Bets % (Tickets)", 0, 100, 45)

# --- 3. CALCULATIONS ---
a_win_p = calculate_poisson_win_prob(a_est, h_est)
a_ev = calculate_ev(a_win_p, a_ml)
sharp_diff = hnd - bets

# --- 4. TACTICAL SCOUTING REPORTS (The "Notes" Section) ---
st.header(f"📈 Tactical Report: {away_t} @ {home_t}")

m1, m2, m3 = st.columns(3)
m1.metric(f"{away_t} Win Probability", f"{a_win_p:.1%}")
m2.metric("Away Edge (EV)", f"{a_ev:.2%}")
m3.metric("Sharp Discrepancy", f"{sharp_diff}%")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🎯 Model Analysis")
    st.write(f"Based on your **{a_est}** to **{h_est}** EST Score projection:")
    
    if a_win_p > 0.55:
        st.success(f"**Heavy Favorite**: Model gives {away_t} a strong statistical advantage.")
    elif a_win_p < 0.40:
        st.error(f"**Underdog Status**: The {away_t} faces a significant climb based on current lambdas.")
    
    if abs(a_ev) > 0.08:
        st.warning(f"💡 **Market Inefficiency**: There is a significant {a_ev:.1%} EV gap. Possible mispricing on the MoneyML.")

with col_right:
    st.subheader("🐳 Institutional Flow (Sharp Notes)")
    if sharp_diff > 15:
        st.info(f"**Sharp Alert**: Large money is moving toward {away_t} despite lower ticket counts.")
    elif sharp_diff < -15:
        st.info(f"**Sharp Alert**: Large money is backing {home_t}. Public is on the other side.")
    else:
        st.write("⚖️ **Market Balance**: Handle and Bets are tracking closely. No major sharp divergence detected.")

st.info(f"📝 **Note**: This model prioritizes implied win percentages over estimated runs.")
