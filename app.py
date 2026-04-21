import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import pybaseball as pyb  # Import the whole library as a shortcut
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="MLB Value Scanner", layout="wide")
LEAGUE_AVG_RPG = 4.46

# --- POISSON ENGINE ---
def calculate_win_probabilities(away_lambda, home_lambda, max_runs=15):
    scores = np.arange(0, max_runs + 1)
    away_probs = poisson.pmf(scores, away_lambda)
    home_probs = poisson.pmf(scores, home_lambda)
    prob_matrix = np.outer(away_probs, home_probs)
    
    away_win_prob = np.sum(np.tril(prob_matrix, -1).T)
    home_win_prob = np.sum(np.tril(prob_matrix, -1))
    
    # Normalize to 100% (removing tie probability)
    total_decisive_prob = away_win_prob + home_win_prob
    if total_decisive_prob == 0: return 0.5, 0.5
    return (away_win_prob / total_decisive_prob), (home_win_prob / total_decisive_prob)

def odds_to_prob(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

# --- APP UI ---
st.title("⚾ MLB Value Scanner v1.0")
st.subheader("Automated Poisson Distribution & Value Finder")

# 1. DATA INGESTION
@st.cache_data(ttl=3600)
def get_mlb_data():
    # Pulling current season stats
    current_year = datetime.datetime.now().year
    batting = team_batting(current_year)[['Team', 'R', 'G']]
    batting['Runs/GM'] = batting['R'] / batting['G']
    
    pitching = team_pitching(current_year)[['Team', 'R', 'G']]
    pitching['RA/GM'] = pitching['R'] / pitching['G']
    
    df = pd.merge(batting[['Team', 'Runs/GM']], pitching[['Team', 'RA/GM']], on='Team')
    return df

try:
    stats_df = get_mlb_data()
    st.success("Live MLB Stats Loaded Successfully")
except:
    st.error("Could not fetch live stats. Using manual input mode.")
    stats_df = pd.DataFrame(columns=['Team', 'Runs/GM', 'RA/GM'])

# 2. MATCHUP INPUT
st.markdown("### Today's Matchups")
num_games = st.number_input("Number of Games to Analyze", min_value=1, max_value=16, value=5)

input_data = []
cols = st.columns(4)

for i in range(num_games):
    with st.expander(f"Game {i+1}", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        away_team = c1.selectbox(f"Away Team", stats_df['Team'].tolist(), key=f"away_{i}")
        home_team = c2.selectbox(f"Home Team", stats_df['Team'].tolist(), key=f"home_{i}")
        away_odds = c3.number_input(f"Away ML (e.g. -110)", value=-110, key=f"a_odds_{i}")
        home_odds = c4.number_input(f"Home ML (e.g. +105)", value=100, key=f"h_odds_{i}")
        
        # Get Stats
        a_stats = stats_df[stats_df['Team'] == away_team].iloc[0]
        h_stats = stats_df[stats_df['Team'] == home_team].iloc[0]
        
        # Calculations
        a_lambda = a_stats['Runs/GM'] * (h_stats['RA/GM'] / LEAGUE_AVG_RPG)
        h_lambda = h_stats['Runs/GM'] * (a_stats['RA/GM'] / LEAGUE_AVG_RPG)
        
        a_win_p, h_win_p = calculate_win_probabilities(a_lambda, h_lambda)
        
        v_away_p = odds_to_prob(away_odds)
        v_home_p = odds_to_prob(home_odds)
        
        input_data.append({
            "Away": away_team,
            "Home": home_team,
            "Proj Away": round(a_lambda, 2),
            "Proj Home": round(h_lambda, 2),
            "Model Away %": f"{round(a_win_p * 100, 2)}%",
            "Vegas Away %": f"{round(v_away_p * 100, 2)}%",
            "Away EV": round(((a_win_p / v_away_p) - 1) * 100, 2),
            "Home EV": round(((h_win_p / v_home_p) - 1) * 100, 2)
        })

# 3. DISPLAY RESULTS
if input_data:
    results_df = pd.DataFrame(input_data)
    
    def color_ev(val):
        color = 'green' if val > 10 else 'lightgreen' if val > 5 else 'white' if val >= 0 else 'red'
        return f'background-color: {color}'

    st.markdown("### Value Analysis")
    st.dataframe(results_df.style.applymap(color_ev, subset=['Away EV', 'Home EV']))

st.info("Strategy Tip: Focus on games with EV > 5% and realistic projected scores.")
