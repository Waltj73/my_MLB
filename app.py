import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import statsapi
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

def highlight_ev(val):
    if isinstance(val, (int, float)):
        if val > 10: return 'background-color: #00FF00; color: black'
        if val > 5: return 'background-color: #90EE90; color: black'
        if val < 0: return 'background-color: #FFCCCB; color: black'
    return ''

# --- DATA INGESTION (Official MLB API) ---
@st.cache_data(ttl=3600)
def get_mlb_data():
    try:
        # Pulls current season standings data directly from MLB
        standings = statsapi.standings_data(leagueId="103,104")
        data = []
        for div in standings:
            for team in standings[div]['teams']:
                data.append({
                    "Team": team['name'],
                    "R": team['runs_scored'],
                    "RA": team['runs_allowed'],
                    "G": team['w'] + team['l']
                })
        
        df = pd.DataFrame(data)
        df['Runs/GM'] = df['R'] / df['G']
        df['RA/GM'] = df['RA'] / df['G']
        return df
    except Exception as e:
        return pd.DataFrame()

# --- APP UI ---
st.title("⚾ MLB Value Scanner v1.0")

stats_df = get_mlb_data()

if stats_df.empty:
    st.warning("⚠️ API Connection Issue. Fallback to Manual Entry.")
    mlb_teams = sorted(["ARI","ATL","BAL","BOS","CHC","CWS","CIN","CLE","COL","DET","HOU","KC","LAA","LAD","MIA","MIL","MIN","NYM","NYY","OAK","PHI","PIT","SD","SF","SEA","STL","TB","TEX","TOR","WSH"])
else:
    st.success("✅ Live Stats Automatically Loaded via MLB API")
    mlb_teams = sorted(stats_df['Team'].tolist())

# 2. MATCHUP INPUT
num_games = st.number_input("Number of Games to Analyze", min_value=1, max_value=16, value=5)
input_data = []

for i in range(num_games):
    with st.expander(f"Game {i+1}", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        a_team = col1.selectbox("Away Team", mlb_teams, key=f"at_{i}")
        h_team = col2.selectbox("Home Team", mlb_teams, key=f"ht_{i}")
        a_odds = col3.number_input("Away ML", value=-110, key=f"ao_{i}")
        h_odds = col4.number_input("Home ML", value=100, key=f"ho_{i}")
        
        # Automatic pull logic
        if not stats_df.empty and a_team in stats_df['Team'].values and h_team in stats_df['Team'].values:
            a_rpg = stats_df[stats_df['Team'] == a_team]['Runs/GM'].values[0]
            a_ra = stats_df[stats_df['Team'] == a_team]['RA/GM'].values[0]
            h_rpg = stats_df[stats_df['Team'] == h_team]['Runs/GM'].values[0]
            h_ra = stats_df[stats_df['Team'] == h_team]['RA/GM'].values[0]
        else:
            # Manual fallback ONLY if API fails
            sc1, sc2, sc3, sc4 = st.columns(4)
            a_rpg = sc1.number_input(f"{a_team} R/G", value=4.50, step=0.01, key=f"ar_{i}")
            a_ra = sc2.number_input(f"{a_team} RA/G", value=4.50, step=0.01, key=f"ara_{i}")
            h_rpg = sc3.number_input(f"{h_team} R/G", value=4.50, step=0.01, key=f"hr_{i}")
            h_ra = sc4.number_input(f"{h_team} RA/G", value=4.50, step=0.01, key=f"hra_{i}")
        
        # Calculations
        a_lambda = a_rpg * (h_ra / LEAGUE_AVG_RPG)
        h_lambda = h_rpg * (a_ra / LEAGUE_AVG_RPG)
        a_win_p, h_win_p = calculate_win_probabilities(a_lambda, h_lambda)
        v_a_p, v_h_p = odds_to_prob(a_odds), odds_to_prob(h_odds)
        
        input_data.append({
            "Away": a_team, "Home": h_team,
            "Proj Away": round(a_lambda, 2), "Proj Home": round(h_lambda, 2),
            "Model Away %": f"{round(a_win_p * 100, 1)}%",
            "Vegas Away %": f"{round(v_a_p * 100, 1)}%",
            "Away EV": round(((a_win_p / v_a_p) - 1) * 100, 2),
            "Home EV": round(((h_win_p / v_h_p) - 1) * 100, 2)
        })

# 3. DISPLAY RESULTS
if input_data:
    res_df = pd.DataFrame(input_data)
    st.markdown("---")
    st.markdown("### Value Analysis")
    st.dataframe(res_df.style.map(highlight_ev, subset=['Away EV', 'Home EV']), use_container_width=True)
