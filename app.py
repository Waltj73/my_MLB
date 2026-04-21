import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# -----------------------------
# CONFIG
# -----------------------------
LEAGUE_ERA = 4.20
EDGE_THRESHOLD = 5
ELITE_EDGE = 10

# -----------------------------
# FUNCTIONS
# -----------------------------

def implied_prob(odds):
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)

def pitcher_adjustment(era):
    factor = era / LEAGUE_ERA
    return min(max(factor, 0.8), 1.2)

def batting_adjustment(wrc):
    return wrc / 100

def expected_runs(base_runs, opp_pitcher_era, team_wrc, split_wrc):
    pitch_adj = pitcher_adjustment(opp_pitcher_era)
    bat_adj = batting_adjustment(team_wrc)
    split_adj = batting_adjustment(split_wrc)

    return base_runs * pitch_adj * bat_adj * split_adj

def poisson_win_prob(lambda_a, lambda_b, max_runs=10):
    prob = 0
    for i in range(max_runs):
        for j in range(max_runs):
            if i > j:
                prob += poisson.pmf(i, lambda_a) * poisson.pmf(j, lambda_b)
    return prob

def expected_value(win_prob, odds):
    if odds > 0:
        return (win_prob * odds) - ((1 - win_prob) * 100)
    else:
        return (win_prob * 100) - ((1 - win_prob) * abs(odds))

# -----------------------------
# UI
# -----------------------------

st.set_page_config(page_title="my_MLB", layout="wide")

st.title("⚾ my_MLB Betting Model")

st.markdown("Upload your daily game file or use the default dataset.")

# -----------------------------
# FILE UPLOAD
# -----------------------------

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    st.warning("Using default sample data. Upload your own CSV.")
    
    df = pd.DataFrame({
        "Game": ["HOU vs CLE", "PHI vs CHC"],
        "Away Team": ["HOU", "PHI"],
        "Home Team": ["CLE", "CHC"],
        "Away Base Runs": [4.8, 4.6],
        "Home Base Runs": [4.2, 4.3],
        "Away Pitcher ERA": [3.80, 3.20],
        "Home Pitcher ERA": [4.50, 4.80],
        "Away wRC+": [110, 108],
        "Home wRC+": [98, 95],
        "Away Split wRC+": [105, 102],
        "Home Split wRC+": [97, 96],
        "Away Odds": [-105, -115],
        "Home Odds": [-115, -105],
    })

# -----------------------------
# CALCULATIONS
# -----------------------------

results = []

for _, row in df.iterrows():

    away_lambda = expected_runs(
        row["Away Base Runs"],
        row["Home Pitcher ERA"],
        row["Away wRC+"],
        row["Away Split wRC+"]
    )

    home_lambda = expected_runs(
        row["Home Base Runs"],
        row["Away Pitcher ERA"],
        row["Home wRC+"],
        row["Home Split wRC+"]
    )

    away_win = poisson_win_prob(away_lambda, home_lambda)
    home_win = 1 - away_win

    away_vegas = implied_prob(row["Away Odds"])
    home_vegas = implied_prob(row["Home Odds"])

    away_diff = (away_win - away_vegas) * 100
    home_diff = (home_win - home_vegas) * 100

    away_ev = expected_value(away_win, row["Away Odds"])
    home_ev = expected_value(home_win, row["Home Odds"])

    results.append({
        "Game": row["Game"],

        "Away Team": row["Away Team"],
        "Home Team": row["Home Team"],

        "Away Win %": round(away_win * 100, 2),
        "Home Win %": round(home_win * 100, 2),

        "Away Diff": round(away_diff, 2),
        "Home Diff": round(home_diff, 2),

        "Away EV": round(away_ev, 2),
        "Home EV": round(home_ev, 2),
    })

results_df = pd.DataFrame(results)

# -----------------------------
# DISPLAY MAIN TABLE
# -----------------------------

st.subheader("📊 Full Slate")

st.dataframe(results_df, use_container_width=True)

# -----------------------------
# TOP PLAYS
# -----------------------------

top_plays = results_df[
    (results_df["Away Diff"] >= EDGE_THRESHOLD) |
    (results_df["Home Diff"] >= EDGE_THRESHOLD)
]

st.subheader("🟢 Top Plays (Edge ≥ 5%)")
st.dataframe(top_plays, use_container_width=True)

# -----------------------------
# ELITE PLAYS
# -----------------------------

elite_plays = results_df[
    (results_df["Away Diff"] >= ELITE_EDGE) |
    (results_df["Home Diff"] >= ELITE_EDGE)
]

st.subheader("🔥 Elite Plays (Edge ≥ 10%)")
st.dataframe(elite_plays, use_container_width=True)

# -----------------------------
# AVOID LIST
# -----------------------------

avoid = results_df[
    (results_df["Away EV"] < 0) &
    (results_df["Home EV"] < 0)
]

st.subheader("❌ Avoid (Negative EV Both Sides)")
st.dataframe(avoid, use_container_width=True)

# -----------------------------
# BEST PICKS SUMMARY
# -----------------------------

st.subheader("🎯 Best Picks (Auto Ranked)")

best = results_df.copy()

best["Best Diff"] = best[["Away Diff", "Home Diff"]].max(axis=1)
best = best.sort_values(by="Best Diff", ascending=False)

st.dataframe(best[["Game", "Best Diff"]], use_container_width=True)
