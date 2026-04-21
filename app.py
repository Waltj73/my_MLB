import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import statsapi
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="MLB Daily Scanner", layout="wide")
LEAGUE_AVG_RPG = 4.46

# --- MATH ENGINE ---
def calculate_win_probabilities(away_lambda, home_lambda, max_runs=15):
    scores = np.arange(0, max_runs + 1)
    away_probs = poisson.pmf(scores, away_lambda)
    home_probs = poisson.pmf(scores, home_lambda)
    prob_matrix = np.outer(away_probs, home_probs)
    away_win_prob = np.sum(np.tril(prob_matrix, -1).T)
    home_win_prob = np.sum(np.tril(prob_matrix, -1))
    total = away_win_prob + home_win_prob
    return (away_win_prob / total), (home_win_prob / total) if total > 0 else (0.5, 0.5)

def odds_to_prob(american_odds):
    if american_odds > 0: return 100 / (american_odds + 100)
    return abs(american_odds) / (abs(american_odds) + 100)

def color_ev(val):
    if val > 10: return 'background-color: #00FF00; color: black'
    if val > 5: return 'background-color: #90EE90; color: black'
    if val < -5: return 'background-color: #FFCCCB; color: black'
    return ''

# --- DATA AUTOMATION ---
@st.cache_data(ttl=3600)
def get_full_slate():
    # 1. Pull Team Stats
    standings = statsapi.standings_data(leagueId="103,104")
    stats_list = []
    for div in standings:
        for team in standings[div]['teams']:
            stats_list.append({
                "Team": team['name'],
                "RPG": team['runs_scored'] / (team['w'] + team['l']),
                "RAPG": team['runs_allowed'] / (team['w'] + team['l'])
            })
    stats_df = pd.DataFrame(stats_list)

    # 2. Pull Today's Schedule
    today = datetime.now().strftime('%Y-%m-%d')
    sched = statsapi.schedule(date=today)
    
    slate = []
    for game in sched:
        if game['status'] == 'Scheduled' or game['status'] == 'Pre-Game':
            a_name, h_name = game['away_name'], game['home_name']
            if a_name in stats_df['Team'].values and h_name in stats_df['Team'].values:
                a_s = stats_df[stats_df['Team'] == a_name].iloc[0]
                h_s = stats_df[stats_df['Team'] == h_name].iloc[0]
                
                # Math
                a_l = a_s['RPG'] * (h_s['RAPG'] / LEAGUE_AVG_RPG)
                h_l = h_s['RPG'] * (a_s['RAPG'] / LEAGUE_AVG_RPG)
                a_p, h_p = calculate_win_probabilities(a_l, h_l)
                
                slate.append({
                    "Matchup": f"{a_name} @ {h_name}",
                    "Away": a_name, "Home": h_name,
                    "Model_Away_P": a_p, "Model_Home_P": h_p,
                    "Proj_Score": f"{round(a_l, 1)} - {round(h_l, 1)}"
                })
    return pd.DataFrame(slate)

# --- UI ---
st.title("⚾ MLB Automated Value Scanner")
st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d')} | **League Avg:** {LEAGUE_AVG_RPG} R/G")

with st.spinner("Fetching today's slate and live stats..."):
    df = get_full_slate()

if not df.empty:
    st.subheader("Today's Projections")
    st.info("Instructions: Enter the current Moneyline odds for the games you want to scan.")
    
    # Let user input odds into the dataframe directly
    df['Away_ML'] = -110
    df['Home_ML'] = 110
    
    # We use data_editor so you can type directly into the table like a spreadsheet
    edited_df = st.data_editor(
        df[['Matchup', 'Proj_Score', 'Away_ML', 'Home_ML']], 
        hide_index=True,
        use_container_width=True
    )

    # Final Calculation
    results = []
    for index, row in edited_df.iterrows():
        orig_row = df.iloc[index]
        v_a_p = odds_to_prob(row['Away_ML'])
        v_h_p = odds_to_prob(row['Home_ML'])
        
        a_ev = ((orig_row['Model_Away_P'] / v_a_p) - 1) * 100
        h_ev = ((orig_row['Model_Home_P'] / v_h_p) - 1) * 100
        
        results.append({
            "Matchup": row['Matchup'],
            "Model Away %": f"{round(orig_row['Model_Away_P']*100, 1)}%",
            "Model Home %": f"{round(orig_row['Model_Home_P']*100, 1)}%",
            "Away EV": round(a_ev, 2),
            "Home EV": round(h_ev, 2)
        })

    st.markdown("---")
    st.subheader("🚨 Value Analysis")
    res_df = pd.DataFrame(results)
    st.dataframe(res_df.style.map(color_ev, subset=['Away EV', 'Home EV']), use_container_width=True)

else:
    st.error("No games found for today or API is down.")
