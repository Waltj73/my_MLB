import html
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="my_MLB Betting Dashboard", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0/export?format=csv&gid=1240994733"

EV_MIN = 5
EDGE_MIN = 5
TOP_PICK_LIMIT = 5


def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def to_float(x):
    if pd.isna(x):
        return np.nan

    s = str(x).replace("%", "").replace("$", "").replace(",", "").replace("+", "").strip()

    if s == "" or s.upper() in ["#N/A", "#VALUE!", "NAN"]:
        return np.nan

    try:
        return float(s)
    except Exception:
        return np.nan


def to_odds(x):
    val = to_float(x)
    if pd.isna(val):
        return np.nan
    return int(val)


def is_dog(odds):
    return not pd.isna(odds) and odds > 0


@st.cache_data(ttl=300)
def load_sheet():
    return pd.read_csv(SHEET_URL, header=None, dtype=str)


raw = load_sheet()


def parse_games(raw_df):
    games = []

    for i in range(len(raw_df)):
        row = raw_df.iloc[i]

        away_team = clean_text(row.iloc[0])
        home_team = clean_text(row.iloc[1])

        if away_team in ["", "Away Team", "Teams"]:
            continue

        if home_team in ["", "Home Team"]:
            continue

        away_runs = to_float(row.iloc[2])
        home_runs = to_float(row.iloc[3])

        away_odds = to_odds(row.iloc[4])
        home_odds = to_odds(row.iloc[5])

        away_my_odds = to_odds(row.iloc[6])
        home_my_odds = to_odds(row.iloc[7])

        sharp_away = to_float(row.iloc[13])
        sharp_home = to_float(row.iloc[14])
        sharp_dog = clean_text(row.iloc[15])

        away_vegas_win = to_float(row.iloc[16])
        home_vegas_win = to_float(row.iloc[17])

        away_my_win = to_float(row.iloc[18])
        home_my_win = to_float(row.iloc[19])

        away_diff = to_float(row.iloc[20])
        home_diff = to_float(row.iloc[21])

        away_ev = to_float(row.iloc[22])
        home_ev = to_float(row.iloc[23])

        games.append({
            "Away Team": away_team,
            "Home Team": home_team,

            "Away Runs": away_runs,
            "Home Runs": home_runs,

            "Away Odds": away_odds,
            "Home Odds": home_odds,

            "Away My Odds": away_my_odds,
            "Home My Odds": home_my_odds,

            "Sharp Away": sharp_away,
            "Sharp Home": sharp_home,
            "Sharp Dog": sharp_dog,

            "Away Vegas Win %": away_vegas_win,
            "Home Vegas Win %": home_vegas_win,

            "Away My Win %": away_my_win,
            "Home My Win %": home_my_win,

            "Away Diff": away_diff,
            "Home Diff": home_diff,

            "Away EV": away_ev,
            "Home EV": home_ev,
        })

    return pd.DataFrame(games)


results_df = parse_games(raw)


def get_pick_info(row):
    away_ev = row["Away EV"]
    home_ev = row["Home EV"]
    away_diff = row["Away Diff"]
    home_diff = row["Home Diff"]

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
            "Dog Pick": is_dog(row["Away Odds"]),
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
            "Dog Pick": is_dog(row["Home Odds"]),
        })

    return pd.Series({
        "Pick": "PASS",
        "Pick Side": "Pass",
        "Pick Odds": np.nan,
        "Pick EV": max(row["Away EV"], row["Home EV"]),
        "Pick Diff": max(row["Away Diff"], row["Home Diff"]),
        "Pick Win %": np.nan,
        "Pick Vegas Win %": np.nan,
        "Pick Sharp": 0,
        "Dog Pick": False,
    })


def grade_play(ev, diff):
    if ev >= 20 and diff >= 10:
        return "Strong Play"
    if ev >= 10 and diff >= 5:
        return "Playable"
    if ev > 5:
        return "Lean"
    return "Pass"


if results_df.empty:
    st.error("No games found. Check your Google Sheet layout.")
    st.stop()

pick_info = results_df.apply(get_pick_info, axis=1)
results_df = pd.concat([results_df, pick_info], axis=1)

results_df["Pick Grade"] = results_df.apply(
    lambda r: grade_play(r["Pick EV"], r["Pick Diff"]),
    axis=1
)


def cell_style(col, val):
    try:
        v = float(val)
    except Exception:
        v = None

    if col in ["Away EV", "Home EV", "Pick EV", "Away Diff", "Home Diff", "Pick Diff"] and v is not None:
        if v >= 20:
            return "background:#0f9d58;color:white;font-weight:bold;"
        if v >= 10:
            return "background:#b7e1cd;color:black;font-weight:bold;"
        if v > 0:
            return "background:#fff2cc;color:black;"
        if v < 0:
            return "background:#f4c7c3;color:black;"

    if col == "Pick":
        if val != "PASS":
            return "background:#0f9d58;color:white;font-weight:bold;"
        return "background:#eeeeee;color:#777;"

    if col == "Pick Grade":
        if val == "Strong Play":
            return "background:#0f9d58;color:white;font-weight:bold;"
        if val == "Playable":
            return "background:#b7e1cd;color:black;font-weight:bold;"
        if val == "Lean":
            return "background:#fff2cc;color:black;"
        return "background:#eeeeee;color:#777;"

    return ""


def fmt_value(col, val):
    if pd.isna(val):
        return ""

    if isinstance(val, (float, int, np.integer, np.floating)):
        if "%" in col or "Diff" in col or "Sharp" in col:
            return f"{val:.2f}%"
        if "EV" in col:
            return f"{val:.2f}"
        if "Odds" in col:
            return f"{int(val)}"
        return f"{val:.2f}"

    return str(val)


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
        z-index: 2;
    }
    table.mlb-table td {
        padding: 6px;
        border: 1px solid #d1d5db;
        text-align: center;
    }
    </style>
    <div style="overflow-x:auto; max-height:700px;">
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
            text = fmt_value(col, val)
            table += f'<td style="{style}">{html.escape(text)}</td>'
        table += "</tr>"

    table += "</tbody></table></div>"

    st.markdown(table, unsafe_allow_html=True)


def sharp_comment(team, sharp_value):
    try:
        sharp_value = float(sharp_value)
    except Exception:
        sharp_value = 0

    if sharp_value >= 20:
        return f"Strong sharp support is showing on {team}. That strengthens the case because respected money appears to agree with the model."
    if sharp_value >= 10:
        return f"Moderate sharp support is showing on {team}. That gives the play some market confirmation."
    if sharp_value <= -20:
        return f"There is heavy sharp resistance against {team}. The model may still like the play, but this is a warning sign."
    if sharp_value <= -10:
        return f"There is some sharp resistance against {team}. This does not automatically kill the play, but it lowers confidence."

    return "No major sharp signal detected. This is mostly a pure model edge."


def generate_writeup(row):
    if row["Pick"] == "PASS":
        return f"""
### {row['Away Team']} vs {row['Home Team']}

**PASS**

This game does not meet the current EV and difference thresholds.

The model is not showing enough clean separation between market price and projected probability to force a bet.
"""

    team = row["Pick"]
    opponent = row["Home Team"] if row["Pick Side"] == "Away" else row["Away Team"]

    dog_note = (
        "This is an underdog value play. The market is pricing this team lower than your model does."
        if row["Dog Pick"]
        else "This is a favorite play with model support. The key is that the price still appears playable."
    )

    sharp_text = sharp_comment(team, row["Pick Sharp"])

    if row["Sharp Dog"] == team:
        sharp_dog_note = f"The sharp dog column also points toward {team}, which adds another layer of confirmation."
    elif row["Sharp Dog"] != "":
        sharp_dog_note = f"The sharp dog column points toward {row['Sharp Dog']}, so this game has some market tension."
    else:
        sharp_dog_note = "There is no listed sharp dog signal for this matchup."

    return f"""
### {row['Away Team']} vs {row['Home Team']}

## Pick: {team} ML ({int(row['Pick Odds'])})

**Grade:** {row['Pick Grade']}

### Model vs Market

- Vegas Win %: **{row['Pick Vegas Win %']:.2f}%**
- Model Win %: **{row['Pick Win %']:.2f}%**
- Difference: **{row['Pick Diff']:.2f}%**
- Expected Value: **{row['Pick EV']:.2f}**
- Sharp ML: **{row['Pick Sharp']:.2f}%**
- Sharp Dog: **{row['Sharp Dog'] if row['Sharp Dog'] else "None"}**

### Read

{dog_note}

Your model prices {team} better than the market does. The edge over Vegas is **{row['Pick Diff']:.2f}%**, with an EV of **{row['Pick EV']:.2f}**.

Against {opponent}, this qualifies because both the EV and difference thresholds are met.

### Sharp Money

{sharp_text}

{sharp_dog_note}

### Risk Notes

- MLB variance is high.
- Avoid forcing every edge into a parlay.
- Strong favorites can still be overpriced.
- Underdogs carry more volatility.
"""


st.title("⚾ my_MLB Betting Dashboard")
st.caption("Data pulled directly from your Google Sheet.")

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

    if top_picks.empty:
        st.info("No picks met the current filters.")
    else:
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

    if writeup_games.empty:
        st.info("No writeups because no picks met the current filters.")

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
