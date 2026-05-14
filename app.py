import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="my_MLB Betting Dashboard", layout="wide")

# =====================================================
# CONFIG
# =====================================================

EV_MIN = 5
EDGE_MIN = 5
STRONG_EV = 20
STRONG_EDGE = 10
TOP_PICK_LIMIT = 5

# =====================================================
# SAMPLE DATA
# Replace this with your real dataframe / CSV import
# =====================================================

data = {
    "Away Team": ["Washington", "Colorado", "St. Louis", "NY Mets", "Pittsburgh", "Atlanta", "Sacramento", "Tampa Bay", "LA Angels", "Minnesota", "Seattle", "Detroit", "Houston", "Chi Cubs", "NY Yankees"],
    "Home Team": ["Miami", "Philadelphia", "San Diego", "Arizona", "SF Giants", "LA Dodgers", "Baltimore", "Boston", "Toronto", "Cleveland", "Chi Sox", "Kansas City", "Cincinnati", "Texas", "Milwaukee"],

    "Away Odds": [135, 153, 123, -120, -122, 144, 109, 123, 149, 100, -136, 119, 135, -143, -143],
    "Home Odds": [-163, -186, -149, 100, 102, -175, -131, -149, -181, -120, 113, -143, -163, 119, 119],

    "Away My Odds": [296, 604, 283, 113, 131, 427, 120, -114, 418, 147, -287, 172, 165, -172, -182],
    "Home My Odds": [-296, -604, -283, -113, -131, -427, -120, 114, -418, -147, 287, -172, -165, 172, 182],

    "Sharp Away": [44, 2, 0, 26, 2, 13, 12, 0, 0, -28, -8, 0, 0, 2, 3],
    "Sharp Home": [-44, -2, 0, -26, -2, -13, -12, 0, 0, 28, 8, 0, 0, -2, -3],
    "Sharp Dogs": ["Washington", "", "St. Louis", "", "", "Atlanta", "Sacramento", "Tampa Bay", "", "", "Chi Sox", "Detroit", "Houston", "", ""],

    "Away Vegas Win %": [42.55, 39.53, 44.84, 54.55, 54.95, 40.98, 47.85, 44.84, 40.16, 50.00, 57.63, 45.66, 42.55, 58.85, 58.85],
    "Home Vegas Win %": [61.98, 65.03, 59.84, 50.00, 49.50, 63.64, 56.71, 59.84, 64.41, 54.55, 46.95, 58.85, 61.98, 45.66, 45.66],

    "Away My Win %": [25.28, 14.21, 26.13, 46.85, 43.27, 18.98, 45.38, 53.19, 19.30, 40.51, 74.17, 36.71, 37.77, 63.29, 64.54],
    "Home My Win %": [74.72, 85.79, 73.87, 53.15, 56.73, 81.02, 54.62, 46.81, 80.70, 59.49, 25.83, 63.29, 62.23, 36.71, 35.46],

    "Away Diff": [-17.27, -25.31, -18.72, -7.69, -11.69, -22.01, -2.47, 8.35, -20.86, -9.49, 16.54, -8.95, -4.78, 4.44, 5.69],
    "Home Diff": [12.74, 20.75, 14.03, 3.15, 7.23, 17.39, -2.09, -13.03, 16.28, 4.94, -21.12, 4.44, 0.25, -8.95, -10.20],

    "Away EV": [-40.59, -64.04, -41.74, -14.10, -21.27, -53.69, -5.16, 18.61, -51.93, -18.97, 28.70, -19.60, -11.24, 7.54, 9.68],
    "Home EV": [20.56, 31.91, 23.45, 6.29, 14.60, 27.32, -3.68, -21.77, 25.28, 9.06, -44.98, 7.54, 0.41, -19.60, -22.35],
}

sample_df = pd.DataFrame(data)

# =====================================================
# LOAD DATA
# =====================================================

st.sidebar.header("Data")
uploaded_file = st.sidebar.file_uploader("Upload model CSV", type=["csv"])

if uploaded_file is not None:
    results_df = pd.read_csv(uploaded_file)
else:
    results_df = sample_df.copy()

# Clean numeric columns if uploaded from Sheets
numeric_cols = [
    "Away Odds", "Home Odds", "Away My Odds", "Home My Odds",
    "Sharp Away", "Sharp Home",
    "Away Vegas Win %", "Home Vegas Win %",
    "Away My Win %", "Home My Win %",
    "Away Diff", "Home Diff",
    "Away EV", "Home EV"
]

for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = (
            results_df[col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace("+", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .replace("", np.nan)
        )
        results_df[col] = pd.to_numeric(results_df[col], errors="coerce")

# =====================================================
# PICK LOGIC
# =====================================================

def get_pick_info(row):
    away_ev = float(row.get("Away EV", 0) or 0)
    home_ev = float(row.get("Home EV", 0) or 0)
    away_edge = float(row.get("Away Diff", 0) or 0)
    home_edge = float(row.get("Home Diff", 0) or 0)

    away_qualifies = away_ev > EV_MIN and away_edge >= EDGE_MIN
    home_qualifies = home_ev > EV_MIN and home_edge >= EDGE_MIN

    if away_qualifies and (away_ev >= home_ev or not home_qualifies):
        return {
            "Pick": row["Away Team"],
            "Side": "Away",
            "Odds": row["Away Odds"],
            "EV": away_ev,
            "Diff": away_edge,
            "My Win %": row["Away My Win %"],
            "Vegas Win %": row["Away Vegas Win %"],
            "Sharp": row.get("Sharp Away", 0),
            "Opponent": row["Home Team"],
        }

    if home_qualifies and (home_ev > away_ev or not away_qualifies):
        return {
            "Pick": row["Home Team"],
            "Side": "Home",
            "Odds": row["Home Odds"],
            "EV": home_ev,
            "Diff": home_edge,
            "My Win %": row["Home My Win %"],
            "Vegas Win %": row["Home Vegas Win %"],
            "Sharp": row.get("Sharp Home", 0),
            "Opponent": row["Away Team"],
        }

    return {
        "Pick": "PASS",
        "Side": "Pass",
        "Odds": None,
        "EV": max(away_ev, home_ev),
        "Diff": max(away_edge, home_edge),
        "My Win %": None,
        "Vegas Win %": None,
        "Sharp": 0,
        "Opponent": "",
    }


def grade_play(ev, edge, sharp=0):
    if ev >= STRONG_EV and edge >= STRONG_EDGE:
        return "Strong Play"
    if ev >= 10 and edge >= EDGE_MIN:
        return "Playable"
    if ev > EV_MIN:
        return "Lean"
    return "Pass"


def is_underdog(odds):
    try:
        return float(odds) > 0
    except Exception:
        return False

pick_rows = []
for _, row in results_df.iterrows():
    info = get_pick_info(row)
    pick_rows.append(info)

pick_df = pd.DataFrame(pick_rows)

results_df["Pick"] = pick_df["Pick"]
results_df["Pick Side"] = pick_df["Side"]
results_df["Pick Odds"] = pick_df["Odds"]
results_df["Pick EV"] = pick_df["EV"]
results_df["Pick Diff"] = pick_df["Diff"]
results_df["Pick Grade"] = [grade_play(ev, diff, sharp) for ev, diff, sharp in zip(pick_df["EV"], pick_df["Diff"], pick_df["Sharp"])]
results_df["Dog Pick"] = results_df["Pick Odds"].apply(is_underdog)

# =====================================================
# STYLING
# =====================================================

def color_value(val):
    try:
        val = float(val)
    except Exception:
        return ""

    if val >= 20:
        return "background-color: #0f9d58; color: white; font-weight: bold;"
    if val >= 10:
        return "background-color: #b7e1cd; color: black;"
    if val > 0:
        return "background-color: #fff2cc; color: black;"
    if val < 0:
        return "background-color: #f4c7c3; color: black;"
    return ""


def color_pick(val):
    if val == "Strong Play":
        return "background-color: #0f9d58; color: white; font-weight: bold;"
    if val == "Playable":
        return "background-color: #b7e1cd; color: black; font-weight: bold;"
    if val == "Lean":
        return "background-color: #fff2cc; color: black;"
    if val == "Pass":
        return "background-color: #eeeeee; color: #666666;"
    return ""


def style_table(df):
    style_cols = [c for c in ["Away Diff", "Home Diff", "Away EV", "Home EV", "Pick EV", "Pick Diff"] if c in df.columns]
    styled = df.style.applymap(color_value, subset=style_cols)
    if "Pick Grade" in df.columns:
        styled = styled.applymap(color_pick, subset=["Pick Grade"])
    return styled

# =====================================================
# WRITE-UP ENGINE
# =====================================================

def sharp_comment(team, sharp_value):
    try:
        sharp_value = float(sharp_value)
    except Exception:
        sharp_value = 0

    if sharp_value >= 20:
        return f"Strong sharp support is showing on {team}. That strengthens the case."
    if sharp_value >= 10:
        return f"Moderate sharp support is showing on {team}."
    if sharp_value <= -20:
        return f"There is heavy sharp resistance against {team}. Size smaller or be cautious."
    if sharp_value <= -10:
        return f"There is some sharp resistance against {team}."
    return "No major sharp signal detected."


def generate_writeup(row):
    if row["Pick"] == "PASS":
        return f"""
### {row['Away Team']} vs {row['Home Team']}

**PASS**

No clean play based on the current EV and difference thresholds.
"""

    team = row["Pick"]
    opponent = row["Home Team"] if row["Pick Side"] == "Away" else row["Away Team"]
    odds = row["Pick Odds"]
    ev = row["Pick EV"]
    diff = row["Pick Diff"]
    grade = row["Pick Grade"]
    sharp = row["Sharp Away"] if row["Pick Side"] == "Away" else row["Sharp Home"]

    if row["Pick Side"] == "Away":
        model_win = row["Away My Win %"]
        vegas_win = row["Away Vegas Win %"]
    else:
        model_win = row["Home My Win %"]
        vegas_win = row["Home Vegas Win %"]

    dog_note = "This is an underdog value play." if is_underdog(odds) else "This is a favorite play with model support."
    sharp_text = sharp_comment(team, sharp)

    return f"""
### {row['Away Team']} vs {row['Home Team']}

## Pick: {team} ML ({odds})

**Grade:** {grade}

### Model Edge

- Vegas Win %: **{vegas_win:.2f}%**
- Model Win %: **{model_win:.2f}%**
- Difference: **{diff:.2f}%**
- Expected Value: **{ev:.2f}**

### Read

{dog_note}

Your model prices {team} better than the market does. The edge over Vegas is **{diff:.2f}%**, with EV of **{ev:.2f}**.

### Sharp Money

{sharp_text}

### Risk Notes

- MLB variance is high.
- Reduce size when sharp money is strongly against the pick.
- Avoid forcing parlays from every listed edge.
"""

# =====================================================
# DISPLAY
# =====================================================

st.title("MLB Betting Dashboard")

main_tab, top_tab, dogs_tab, writeups_tab, dog_writeups_tab = st.tabs([
    "All Games",
    "Top 5 Picks",
    "Top Underdogs",
    "Pick Writeups",
    "Dog Writeups",
])

with main_tab:
    st.subheader("All Games")
    st.dataframe(style_table(results_df), use_container_width=True, height=650)

with top_tab:
    st.subheader("Top 5 Picks")
    top_picks = (
        results_df[results_df["Pick"] != "PASS"]
        .sort_values(by=["Pick Grade", "Pick EV", "Pick Diff"], ascending=[True, False, False])
        .head(TOP_PICK_LIMIT)
    )
    st.dataframe(style_table(top_picks), use_container_width=True)

with dogs_tab:
    st.subheader("Top Underdog Picks")
    dog_picks = (
        results_df[(results_df["Pick"] != "PASS") & (results_df["Dog Pick"] == True)]
        .sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])
    )
    st.dataframe(style_table(dog_picks), use_container_width=True)

with writeups_tab:
    st.subheader("Writeups for Picks")
    writeup_games = results_df[results_df["Pick"] != "PASS"].sort_values(by="Pick EV", ascending=False)
    for _, row in writeup_games.iterrows():
        st.markdown(generate_writeup(row))
        st.divider()

with dog_writeups_tab:
    st.subheader("Underdog Writeups")
    dog_writeups = results_df[(results_df["Pick"] != "PASS") & (results_df["Dog Pick"] == True)].sort_values(by="Pick EV", ascending=False)
    if dog_writeups.empty:
        st.info("No underdog picks met the current filters.")
    for _, row in dog_writeups.iterrows():
        st.markdown(generate_writeup(row))
        st.divider()
