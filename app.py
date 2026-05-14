import streamlit as st
import pandas as pd

st.set_page_config(page_title="MLB Model Dashboard", layout="wide")

# =====================================================
# SAMPLE DATA
# Replace this section with your real CSV / Sheets import
# =====================================================

data = {
    "Away Team": ["Seattle", "NY Yankees", "Atlanta", "Toronto"],
    "Home Team": ["Chi Sox", "Milwaukee", "LA Dodgers", "LA Angels"],

    "Away Odds": [-136, -143, 144, -181],
    "Home Odds": [113, 119, -175, 149],

    "Away Vegas Win %": [57.63, 58.85, 40.98, 64.41],
    "Home Vegas Win %": [46.95, 45.66, 63.64, 40.16],

    "Away My Win %": [74.17, 64.54, 18.98, 19.30],
    "Home My Win %": [25.83, 35.46, 81.02, 80.70],

    "Away Diff": [16.54, 5.69, -22.01, -20.86],
    "Home Diff": [-15.38, -10.20, 17.39, 16.28],

    "Away EV": [28.70, 9.68, -53.69, -51.93],
    "Home EV": [-44.98, -22.35, 27.32, 25.28],

    "Sharp Away": [-8, 3, 13, 0],
    "Sharp Home": [8, -3, -13, 0],
}

results_df = pd.DataFrame(data)

# =====================================================
# HELPERS
# =====================================================

def moneyline_label(row):
    away_ev = row["Away EV"]
    home_ev = row["Home EV"]

    away_edge = row["Away Diff"]
    home_edge = row["Home Diff"]

    if away_ev > home_ev and away_ev > 5 and away_edge > 0:
        return row["Away Team"], "away"

    if home_ev > away_ev and home_ev > 5 and home_edge > 0:
        return row["Home Team"], "home"

    return "PASS", "pass"


def grade_play(ev, edge):
    if ev >= 25 and edge >= 10:
        return "🔥 Strong Play"

    if ev >= 10 and edge >= 5:
        return "✅ Playable"

    if ev >= 5:
        return "⚠️ Lean"

    return "❌ Pass"


def sharp_comment(side, sharp_value):
    if sharp_value >= 20:
        return f"Strong sharp support on the {side}."

    if sharp_value >= 10:
        return f"Moderate sharp support on the {side}."

    if sharp_value <= -20:
        return f"Heavy sharp resistance against the {side}."

    if sharp_value <= -10:
        return f"Some sharp resistance against the {side}."

    return "No major sharp signal detected."


# =====================================================
# WRITE-UP ENGINE
# =====================================================

def generate_game_writeup(row):
    pick, side = moneyline_label(row)

    if side == "pass":
        return f"""
### {row['Away Team']} vs {row['Home Team']}

**PASS** — No clear edge from the model.

- Market and model are relatively aligned
- EV not strong enough
- No meaningful statistical advantage
"""

    if side == "away":
        team = row["Away Team"]
        opponent = row["Home Team"]

        ev = row["Away EV"]
        edge = row["Away Diff"]
        win_pct = row["Away My Win %"]
        vegas_pct = row["Away Vegas Win %"]
        odds = row["Away Odds"]
        sharp = row["Sharp Away"]

    else:
        team = row["Home Team"]
        opponent = row["Away Team"]

        ev = row["Home EV"]
        edge = row["Home Diff"]
        win_pct = row["Home My Win %"]
        vegas_pct = row["Home Vegas Win %"]
        odds = row["Home Odds"]
        sharp = row["Sharp Home"]

    grade = grade_play(ev, edge)
    sharp_text = sharp_comment(team, sharp)

    return f"""
### {row['Away Team']} vs {row['Home Team']}

## 🎯 Pick: {team} ML ({odds})

**Grade:** {grade}

---

### 📊 Model Edge

- Vegas Win %: **{vegas_pct:.2f}%**
- Model Win %: **{win_pct:.2f}%**
- Difference: **{edge:.2f}%**
- Expected Value: **{ev:.2f}**

---

### 🧠 Analysis

Your model projects {team} as undervalued by the market.

The current betting line implies a lower probability than your projections suggest, creating a positive EV opportunity.

Against {opponent}, the statistical edge is large enough to justify consideration as a moneyline play.

---

### 💰 Sharp Money

{sharp_text}

---

### ⚠️ Risk Notes

- MLB variance is high
- Bullpen volatility matters
- Do not over-size positions based on one edge alone
"""


# =====================================================
# BUILD PICKS COLUMN
# =====================================================

picks = []

for _, row in results_df.iterrows():
    pick, side = moneyline_label(row)
    picks.append(pick)

results_df["Pick"] = picks


# =====================================================
# MAIN DASHBOARD
# =====================================================

st.title("⚾ MLB Betting Dashboard")

st.subheader("📋 Model Table")
st.dataframe(results_df, use_container_width=True)


# =====================================================
# TOP PLAYS
# =====================================================

st.subheader("🔥 Top Plays")

play_df = results_df[
    (
        (results_df["Away EV"] > 10)
        |
        (results_df["Home EV"] > 10)
    )
]

st.dataframe(play_df, use_container_width=True)


# =====================================================
# AUTO WRITE-UPS
# =====================================================

st.subheader("📝 Auto Game Write-Ups")

for _, row in results_df.iterrows():
    st.markdown(generate_game_writeup(row))
    st.divider()





# What This Adds To Your App

This version automatically generates:

* Picks
* Grades
* EV analysis
* Sharp money commentary
* PASS filters
* Auto write-ups for every game



# What You Need To Replace

Replace this:


results_df = pd.DataFrame(data)


with:


results_df = YOUR_REAL_MODEL_DF


using your real Google Sheet or calculation engine.



# Required Column Names

Your dataframe must contain:


Away Team
Home Team
Away Odds
Home Odds
Away Vegas Win %
Home Vegas Win %
Away My Win %
Home My Win %
Away Diff
Home Diff
Away EV
Home EV
Sharp Away
Sharp Home




# Future Upgrades

You can later add:

* Confidence meter
* Kelly sizing
* Sharp fade warnings
* Public fade signals
* Over/Under analysis
* Pitcher analysis
* Color-coded cards
* AI-generated summaries
* Discord export
* Telegram alerts
