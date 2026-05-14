import streamlit as st
import pandas as pd
import numpy as np
import html

st.set_page_config(page_title="my_MLB Betting Dashboard", layout="wide")

EV_MIN = 5
EDGE_MIN = 5
STRONG_EV = 20
STRONG_EDGE = 10
TOP_PICK_LIMIT = 5

data = {
    "Away Team": [
        "Washington", "Colorado", "St. Louis", "NY Mets", "Pittsburgh",
        "Atlanta", "Sacramento", "Tampa Bay", "LA Angels", "Minnesota",
        "Seattle", "Detroit", "Houston", "Chi Cubs", "NY Yankees"
    ],
    "Home Team": [
        "Miami", "Philadelphia", "San Diego", "Arizona", "SF Giants",
        "LA Dodgers", "Baltimore", "Boston", "Toronto", "Cleveland",
        "Chi Sox", "Kansas City", "Cincinnati", "Texas", "Milwaukee"
    ],
    "Away Odds": [135, 153, 123, -120, -122, 144, 109, 123, 149, 100, -136, 119, 135, -143, -143],
    "Home Odds": [-163, -186, -149, 100, 102, -175, -131, -149, -181, -120, 113, -143, -163, 119, 119],
    "Sharp Away": [44, 2, 0, 26, 2, 13, 12, 0, 0, -28, -8, 0, 0, 2, 3],
    "Sharp Home": [-44, -2, 0, -26, -2, -13, -12, 0, 0, 28, 8, 0, 0, -2, -3],
    "Away Vegas Win %": [42.55, 39.53, 44.84, 54.55, 54.95, 40.98, 47.85, 44.84, 40.16, 50.00, 57.63, 45.66, 42.55, 58.85, 58.85],
    "Home Vegas Win %": [61.98, 65.03, 59.84, 50.00, 49.50, 63.64, 56.71, 59.84, 64.41, 54.55, 46.95, 58.85, 61.98, 45.66, 45.66],
    "Away My Win %": [25.28, 14.21, 26.13, 46.85, 43.27, 18.98, 45.38, 53.19, 19.30, 40.51, 74.17, 36.71, 37.77, 63.29, 64.54],
    "Home My Win %": [74.72, 85.79, 73.87, 53.15, 56.73, 81.02, 54.62, 46.81, 80.70, 59.49, 25.83, 63.29, 62.23, 36.71, 35.46],
    "Away Diff": [-17.27, -25.31, -18.72, -7.69, -11.69, -22.01, -2.47, 8.35, -20.86, -9.49, 16.54, -8.95, -4.78, 4.44, 5.69],
    "Home Diff": [12.74, 20.75, 14.03, 3.15, 7.23, 17.39, -2.09, -13.03, 16.28, 4.94, -21.12, 4.44, 0.25, -8.95, -10.20],
    "Away EV": [-40.59, -64.04, -41.74, -14.10, -21.27, -53.69, -5.16, 18.61, -51.93, -18.97, 28.70, -19.60, -11.24, 7.54, 9.68],
    "Home EV": [20.56, 31.91, 23.45, 6.29, 14.60, 27.32, -3.68, -21.77, 25.28, 9.06, -44.98, 7.54, 0.41, -19.60, -22.35],
}

results_df = pd.DataFrame(data)

def get_pick_info(row):
    away_ev = float(row["Away EV"])
    home_ev = float(row["Home EV"])
    away_diff = float(row["Away Diff"])
    home_diff = float(row["Home Diff"])

    away_play = away_ev > EV_MIN and away_diff >= EDGE_MIN
    home_play = home_ev > EV_MIN and home_diff >= EDGE_MIN

    if away_play and (away_ev >= home_ev or not home_play):
        return pd.Series({
            "Pick": row["Away Team"],
            "Pick Side": "Away",
            "Pick Odds": row["Away Odds"],
            "Pick EV": away_ev,
            "Pick Diff": away_diff,
            "Pick Win %": row["Away My Win %"],
            "Pick Vegas Win %": row["Away Vegas Win %"],
            "Pick Sharp": row["Sharp Away"],
            "Dog Pick": row["Away Odds"] > 0,
        })

    if home_play and (home_ev > away_ev or not away_play):
        return pd.Series({
            "Pick": row["Home Team"],
            "Pick Side": "Home",
            "Pick Odds": row["Home Odds"],
            "Pick EV": home_ev,
            "Pick Diff": home_diff,
            "Pick Win %": row["Home My Win %"],
            "Pick Vegas Win %": row["Home Vegas Win %"],
            "Pick Sharp": row["Sharp Home"],
            "Dog Pick": row["Home Odds"] > 0,
        })

    return pd.Series({
        "Pick": "PASS",
        "Pick Side": "Pass",
        "Pick Odds": np.nan,
        "Pick EV": max(away_ev, home_ev),
        "Pick Diff": max(away_diff, home_diff),
        "Pick Win %": np.nan,
        "Pick Vegas Win %": np.nan,
        "Pick Sharp": 0,
        "Dog Pick": False,
    })


def grade_play(ev, diff):
    if ev >= STRONG_EV and diff >= STRONG_EDGE:
        return "Strong Play"
    if ev >= 10 and diff >= EDGE_MIN:
        return "Playable"
    if ev > EV_MIN:
        return "Lean"
    return "Pass"


pick_info = results_df.apply(get_pick_info, axis=1)
results_df = pd.concat([results_df, pick_info], axis=1)
results_df["Pick Grade"] = results_df.apply(
    lambda row: grade_play(row["Pick EV"], row["Pick Diff"]), axis=1
)

def cell_style(col, val):
    if col in ["Away EV", "Home EV", "Pick EV", "Away Diff", "Home Diff", "Pick Diff"]:
        try:
            v = float(val)
            if v >= 20:
                return "background:#0f9d58;color:white;font-weight:bold;"
            if v >= 10:
                return "background:#b7e1cd;color:black;font-weight:bold;"
            if v > 0:
                return "background:#fff2cc;color:black;"
            if v < 0:
                return "background:#f4c7c3;color:black;"
        except Exception:
            return ""

    if col == "Pick Grade":
        if val == "Strong Play":
            return "background:#0f9d58;color:white;font-weight:bold;"
        if val == "Playable":
            return "background:#b7e1cd;color:black;font-weight:bold;"
        if val == "Lean":
            return "background:#fff2cc;color:black;"
        if val == "Pass":
            return "background:#eeeeee;color:#777;"

    if col == "Pick":
        if val != "PASS":
            return "background:#0f9d58;color:white;font-weight:bold;"
        return "background:#eeeeee;color:#777;"

    return ""


def render_colored_table(df):
    cols = list(df.columns)
    table = """
    <style>
    table.mlb-table {
        border-collapse: collapse;
        width: 100%;
        font-size: 13px;
    }
    table.mlb-table th {
        background: #111827;
        color: white;
        padding: 7px;
        border: 1px solid #d1d5db;
        text-align: center;
        position: sticky;
        top: 0;
    }
    table.mlb-table td {
        padding: 6px;
        border: 1px solid #d1d5db;
        text-align: center;
    }
    </style>
    <table class="mlb-table">
    <thead><tr>
    """

    for col in cols:
        table += f"<th>{html.escape(str(col))}</th>"
    table += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        table += "<tr>"
        for col in cols:
            val = row[col]
            style = cell_style(col, val)

            if isinstance(val, float):
                if "%" in col or "Diff" in col:
                    text = f"{val:.2f}%"
                elif "EV" in col:
                    text = f"{val:.2f}"
                elif "Odds" in col and not pd.isna(val):
                    text = f"{int(val)}"
                else:
                    text = f"{val:.2f}"
            elif pd.isna(val):
                text = ""
            else:
                text = str(val)

            table += f'<td style="{style}">{html.escape(text)}</td>'
        table += "</tr>"

    table += "</tbody></table>"
    st.markdown(table, unsafe_allow_html=True)


def sharp_comment(team, sharp_value):
    sharp_value = float(sharp_value)

    if sharp_value >= 20:
        return f"Strong sharp support is showing on {team}. That strengthens the case and suggests respected money agrees with the model."
    if sharp_value >= 10:
        return f"Moderate sharp support is showing on {team}. That gives the play some market confirmation."
    if sharp_value <= -20:
        return f"There is heavy sharp resistance against {team}. The model may still like the play, but this is a warning sign."
    if sharp_value <= -10:
        return f"There is some sharp resistance against {team}. This does not kill the play, but it lowers confidence."
    return "No major sharp signal detected. This is mostly a pure model edge rather than a sharp-backed play."


def generate_writeup(row):
    if row["Pick"] == "PASS":
        return f"""
### {row['Away Team']} vs {row['Home Team']}

**PASS**

This game does not meet the current betting threshold.

The model does not show enough clean separation between projected value, market price, and EV. This is the type of game where forcing action can create unnecessary risk.
"""

    team = row["Pick"]
    opponent = row["Home Team"] if row["Pick Side"] == "Away" else row["Away Team"]

    odds = int(row["Pick Odds"])
    ev = row["Pick EV"]
    diff = row["Pick Diff"]
    grade = row["Pick Grade"]
    model_win = row["Pick Win %"]
    vegas_win = row["Pick Vegas Win %"]
    sharp = row["Pick Sharp"]

    dog_note = (
        "This is an underdog value play. The market is pricing this team as less likely to win than your model suggests."
        if row["Dog Pick"]
        else "This is a favorite play with model support. The key is not just that the team is favored, but that your model believes the current price is still short."
    )

    if grade == "Strong Play":
        confidence_text = "This is one of the stronger plays on the board because both EV and model edge are clearly above threshold."
    elif grade == "Playable":
        confidence_text = "This is a playable edge, but not quite the strongest tier. It is worth consideration, especially as a straight bet."
    else:
        confidence_text = "This is more of a lean than a core play. It should be sized smaller or used only if you are comfortable with the risk."

    sharp_text = sharp_comment(team, sharp)

    return f"""
### {row['Away Team']} vs {row['Home Team']}

## 🎯 Pick: {team} ML ({odds})

**Grade:** {grade}

---

### 📊 Model vs Market

- Vegas implied win probability: **{vegas_win:.2f}%**
- Your model win probability: **{model_win:.2f}%**
- Difference: **{diff:.2f}%**
- Expected Value: **{ev:.2f}**

---

### 🧠 Why This Is a Play

{dog_note}

Your model is showing a meaningful gap between the market price and your projected probability. That gap is what creates the betting value here.

Against {opponent}, the model is not just saying “{team} can win.” It is saying the current moneyline is not fully pricing in the probability your numbers assign to this matchup.

{confidence_text}

---

### 💰 Sharp Money Read

{sharp_text}

Sharp money should not override the model by itself, but it can help explain confidence. If sharp action agrees with the play, that strengthens it. If sharp action is against the play, the bet may still be valid, but it should be sized more carefully.

---

### ⚠️ Risk Notes

- MLB has high variance, even on strong edges.
- Avoid stacking too many correlated moneyline favorites in one parlay.
- If this is an underdog, expect more volatility.
- If this is a heavy favorite, make sure the price is still worth paying.
"""


st.title("⚾ my_MLB Betting Dashboard")

main_tab, top_tab, dogs_tab, writeups_tab, dog_writeups_tab = st.tabs([
    "All Games",
    "Top 5 Picks",
    "Top Underdogs",
    "Pick Writeups",
    "Dog Writeups",
])

with main_tab:
    st.subheader("All Games")
    render_colored_table(results_df)

with top_tab:
    st.subheader("Top 5 Picks")
    top_picks = (
        results_df[results_df["Pick"] != "PASS"]
        .sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])
        .head(TOP_PICK_LIMIT)
    )
    render_colored_table(top_picks)

with dogs_tab:
    st.subheader("Top Underdog Picks")
    dog_picks = (
        results_df[(results_df["Pick"] != "PASS") & (results_df["Dog Pick"] == True)]
        .sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])
    )
    if dog_picks.empty:
        st.info("No underdog picks met the current filters.")
    else:
        render_colored_table(dog_picks)

with writeups_tab:
    st.subheader("Detailed Writeups for Picks")
    writeup_games = (
        results_df[results_df["Pick"] != "PASS"]
        .sort_values(by="Pick EV", ascending=False)
    )

    for _, row in writeup_games.iterrows():
        st.markdown(generate_writeup(row))
        st.divider()

with dog_writeups_tab:
    st.subheader("Detailed Underdog Writeups")
    dog_writeups = (
        results_df[(results_df["Pick"] != "PASS") & (results_df["Dog Pick"] == True)]
        .sort_values(by="Pick EV", ascending=False)
    )

    if dog_writeups.empty:
        st.info("No underdog picks met the current filters.")

    for _, row in dog_writeups.iterrows():
        st.markdown(generate_writeup(row))
        st.divider()
