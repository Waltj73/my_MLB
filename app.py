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
    if total <= 0:
        return 0.5, 0.5
    return (away_win_prob / total), (home_win_prob / total)

def odds_to_prob(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

def color_ev(val):
    if isinstance(val, (int, float)):
        if val > 10: return 'background-color: #00FF00; color: black'
        if val > 5: return 'background-color: #90EE90; color: black'
        if val < -5: return 'background-color: #FFCCCB; color: black'
    return ''

# --- DATA AUTOMATION ---
@st.cache_data(ttl=3600)
def get_full_slate():
    try:
        # 1. Pull Team Stats
        standings = statsapi.standings_data(leagueId="103,104")
        stats_list = []
        for div in standings:
            for team in standings[div]['teams']:
                games = team.get('w', 0) + team.get('l', 0)
                # SAFETY CHECK: Skip teams with zero games played to avoid division error
                if games > 0:
                    stats_list.append({
                        "Team": team['name'],
                        "RPG": team['runs_scored'] / games,
                        "RAPG": team['runs_allowed'] / games
                    })
        stats_df = pd.DataFrame(stats_list)

        # 2. Pull Today's Schedule
        today = datetime.now().strftime('%Y-%m-%d')
        sched = statsapi.schedule(date=today)
        
        slate = []
        for game in sched:
            if game.get('status') in ['Scheduled', 'Pre-Game']:
                a_name, h_name = game['away_name'], game['home_name']
                if a_name in stats_df['Team'].values and h_name in stats_df['Team'].values:
                    a_s = stats_df[stats_df['Team'] == a_name].iloc[0]
                    h_s = stats_df[stats_df['Team'] == h_name].iloc[0]
                    
                    a_l = a_s['RPG'] * (h_s['RAPG'] / LEAGUE_AVG_RPG)
                    h_l = h_s['RPG'] * (a_s['RAPG'] / LEAGUE_AVG_RPG)
                    a_p, h_p = calculate_win_probabilities(a_l, h_l)
                    
                    slate.append({
                        "Matchup": f"{a_name} @ {h_name}",
                        "Away": a_name, 
                        "Home": h_name,
                        "Model_Away_P": a_p, 
                        "Model_Home_P": h_p,
                        "Proj_Score": f"{round(a_l, 1)} - {round(h_l, 1)}"
                    })
        return pd.DataFrame(slate)
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

# --- UI DISPLAY ---
st.title("⚾ MLB Automated Daily Scanner")

df = get_full_slate()

if not df.empty:
    st.subheader("1. Enter Current Odds")
    
    display_df = df[['Matchup', 'Proj_Score']].copy()
    display_df['Away_ML'] = -110
    display_df['Home_ML'] = 110
    
    edited_df = st.data_editor(
        display_df, 
        hide_index=True,
        use_container_width=True,
        key="odds_editor"
    )

    results = []
    for index, row in edited_df.iterrows():
        orig_data = df.iloc[index]
        v_a_p = odds_to_prob(row['Away_ML'])
        v_h_p = odds_to_prob(row['Home_ML'])
        
        a_ev = ((orig_data['Model_Away_P'] / v_a_p) - 1) * 100
        h_ev = ((orig_data['Model_Home_P'] / v_h_p) - 1) * 100
        
        results.append({
            "Matchup": row['Matchup'],
            "Away Model %": f"{round(orig_data['Model_Away_P']*100, 1)}%",
            "Home Model %": f"{round(orig_data['Model_Home_P']*100, 1)}%",
            "Away EV": round(a_ev, 2),
            "Home EV": round(h_ev, 2)
        })

    st.markdown("---")
    st.subheader("2. Value Analysis (Ranked)")
    res_df = pd.DataFrame(results)
    st.dataframe(
        res_df.style.map(color_ev, subset=['Away EV', 'Home EV']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("No upcoming games found for today.")
