import streamlit as st
import pandas as pd
import math

# -----------------------------
# CONFIG
# -----------------------------
LEAGUE_ERA = 4.20
EDGE_THRESHOLD = 5
ELITE_EDGE = 10

# -----------------------------
# SAFE COLUMN HANDLER
# -----------------------------
def get_col(row, possible_names, default=0):
    for name in possible_names:
        if name in row:
            return row[name]
    return default

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
    return wrc / 100 if wrc != 0 else 1

def expected_runs(base_runs, opp_pitcher_era, team_wrc, split_wrc):
    return (
        base_runs *
        pitcher_adjustment(opp_pitcher_era) *
        batting_adjustment(team_wrc) *
        batting_adjustment(split_wrc)
    )

def poisson_pmf(k, lam):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def win_prob(lambda_a, lambda_b):
    prob = 0
    for i in range(10):
        for j in range(10):
            if i > j:
                prob += poisson_pmf(i, lambda_a) * poisson_pmf(j, lambda_b)
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

uploaded_file = st.file_uploader("Upload your CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    st.warning("Using sample data")
    df = pd.DataFrame({
        "Game": ["HOU vs CLE"],
        "Away Team": ["HOU"],
        "Home Team": ["CLE"],
        "Away Base Runs": [4.8],
        "Home Base Runs": [4.2],
        "Away Pitcher ERA": [3.8],
        "Home Pitcher ERA": [4.5],
        "Away wRC+": [110],
        "Home wRC+": [98],
        "Away Split wRC+": [105],
        "Home Split wRC+": [97],
        "Away Odds": [-105],
        "Home Odds": [-115]
    })

# 🔥 Normalize columns (THIS FIXES YOUR ISSUE)
df.columns = df.columns.str.strip().str.lower()

st.subheader("Detected Columns")
st.write(df.columns.tolist())

# -----------------------------
# CALCULATIONS
# -----------------------------
results = []

for _, row in df.iterrows():

    away_runs = expected_runs(
        get_col(row, ["away base runs", "awaybaseruns"]),
        get_col(row, ["home pitcher era"]),
        get_col(row, ["away wrc+", "away wrc"]),
        get_col(row, ["away split wrc+", "away split"])
    )

    home_runs = expected_runs(
        get_col(row, ["home base runs", "homebaseruns"]),
        get_col(row, ["away pitcher era"]),
        get_col(row, ["home wrc+", "home wrc"]),
        get_col(row, ["home split wrc+", "home split"])
    )

    away_win = win_prob(away_runs, home_runs)
    home_win = 1 - away_win

    away_odds = get_col(row, ["away odds"])
    home_odds = get_col(row, ["home odds"])

    away_vegas = implied_prob(away_odds)
    home_vegas = implied_prob(home_odds)

    away_diff = (away_win - away_vegas) * 100
    home_diff = (home_win - home_vegas) * 100

    away_ev = expected_value(away_win, away_odds)
    home_ev = expected_value(home_win, home_odds)

    results.append({
        "Game": get_col(row, ["game"]),
        "Away Win %": round(away_win * 100, 2),
        "Home Win %": round(home_win * 100, 2),
        "Away Diff": round(away_diff, 2),
        "Home Diff": round(home_diff, 2),
        "Away EV": round(away_ev, 2),
        "Home EV": round(home_ev, 2),
    })

results_df = pd.DataFrame(results)

# -----------------------------
# OUTPUT
# -----------------------------
st.subheader("📊 Full Slate")
st.dataframe(results_df, use_container_width=True)

st.subheader("🟢 Top Plays (Edge ≥ 5%)")
st.dataframe(
    results_df[(results_df["Away Diff"] >= EDGE_THRESHOLD) |
               (results_df["Home Diff"] >= EDGE_THRESHOLD)]
)

st.subheader("🔥 Elite Plays (Edge ≥ 10%)")
st.dataframe(
    results_df[(results_df["Away Diff"] >= ELITE_EDGE) |
               (results_df["Home Diff"] >= ELITE_EDGE)]
)

st.subheader("❌ Avoid (Negative EV Both)")
st.dataframe(
    results_df[(results_df["Away EV"] < 0) &
               (results_df["Home EV"] < 0)]
)
