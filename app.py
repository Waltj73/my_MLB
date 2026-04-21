import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import pybaseball as pyb
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

# 1. DATA INGESTION
@st.cache_data(ttl=3600)
def get_mlb_data():
    try:
        current_year = datetime.datetime.now().year
        batting = pyb.team_batting(current_year)[['Team', 'R', 'G']]
        batting['Runs/GM'] = batting['R'] / batting['G']
        pitching = pyb.team_pitching(current_year)[['Team', 'R', 'G']]
        pitching['RA/GM'] = pitching['R'] / pitching['G']
        return pd.merge(batting[['Team', 'Runs/GM']], pitching[['Team', 'RA/GM']], on='Team')
    except:
        return pd.DataFrame()

stats_df = get_mlb_data()

if stats_df.empty:
    st.warning("⚠️ Live Stats Connection Blocked. Using Manual Entry Mode.")
    # Fallback list of teams
    mlb_teams = ["ATL", "PHI", "NYM", "MIA", "WSH", "CHC", "MIL", "STL", "CIN", "PIT", "LAD", "SF", "SD", "ARI", "COL", "NYY", "BAL", "TOR", "TB", "BOS", "CLE", "MIN", "DET", "KC", "CWS", "HOU", "SEA", "TEX", "LAA", "OAK"]
else:
    st.success("Live MLB Stats Loaded Successfully")
    mlb_teams = stats_df['Team'].tolist()

# 2. MATCHUP INPUT
st.markdown("### Today's Matchups")
num_games = st.number_input("Number of Games", min_value=1, max_value=15, value=3)

input_data = []

for i in range(num_games):
    with st.expander(f"Game {i+1}", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        a_team = c1.selectbox(f"Away Team", mlb_teams, key=f"a_t_{i}")
        h_team = c2.selectbox(f"Home Team", mlb_teams, key=f"h_t_{i}")
        a_odds = c3.number_input(f"Away ML", value=-110, key=f"a_o_{i}")
        h_odds = c4.number_input(f"Home ML", value=100, key=f"h_o_{i}")
        
        # Manual stat entry if live data failed
        if stats_df.empty:
            sc1, sc2, sc3, sc4 = st.columns(4)
            a_rpg = sc1.number_input(f"{a_team} Runs/GM", value=4.5, key=f"a_r_{i}")
            a_ra = sc2.number_input(f"{a_team} RA/GM", value=4.5, key=f"a_ra_{i}")
            h_rpg = sc3.number_input(f"{h_team} Runs/GM", value=4.5, key=f"h_r_{i}")
            h_ra = sc4.number_input(f"{h_team} RA/GM", value=4.5, key=f"h_ra_{i}")
        else:
            a_rpg = stats_df[stats_df['Team'] == a_team]['Runs/GM'].values[0]
            a_ra = stats_df[stats_df['Team'] == a_team]['RA/GM'].values[0]
            h_rpg = stats_df[stats_df['Team'] == h_team]['Runs/GM'].values[0]
            h_ra = stats_df[stats_df['Team'] == h_team]['RA/GM'].values[0]
        
        # Calculation Logic
        a_lambda = a_rpg * (h_ra / LEAGUE_AVG_RPG)
        h_lambda = h_rpg * (a_ra / LEAGUE_AVG_RPG)
        a_win_p, h_win_p = calculate_win_probabilities(a_lambda, h_lambda)
        v_a_p, v_h_p = odds_to_prob(a_odds), odds_to_prob(h_odds)
        
        input_data.append({
            "Away": a_team, "Home": h_team,
            "Proj Away": round(a_lambda, 2), "Proj Home": round(h_lambda, 2),
            "Away EV": round(((a_win_p / v_a_p) - 1) * 100, 2),
            "Home EV": round(((h_win_p / v_h_p) - 1) * 100, 2)
        })

# 3. DISPLAY RESULTS
if input_data:
    res_df = pd.DataFrame(input_data)
    st.markdown("### Value Analysis")
    st.dataframe(res_df.style.applymap(lambda x: 'background-color: #00FF00; color: black' if x > 10 else ('background-color: #90EE90; color: black' if x > 5 else ''), subset=['Away EV', 'Home EV']))
