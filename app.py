import re
import html
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="my_MLB Betting Dashboard", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0/export?format=csv&gid=1240994733"

EV_MIN = 5
EDGE_MIN = 5
TOP_PICK_LIMIT = 5


# =====================================================
# HELPERS
# =====================================================

def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def to_float(x):
    if pd.isna(x):
        return np.nan

    s = str(x)
    s = s.replace("%", "")
    s = s.replace("$", "")
    s = s.replace(",", "")
    s = s.replace("+", "")
    s = s.strip()

    if s == "" or s.upper() in ["#N/A", "#VALUE!"]:
        return np.nan

    try:
        return float(s)
    except Exception:
        return np.nan


def to_odds(x):
    s = clean_text(x)
    s = s.replace("+", "")
    try:
        return int(float(s))
    except Exception:
        return np.nan


def implied_prob(odds):
    if pd.isna(odds):
        return np.nan

    odds = float(odds)

    if odds < 0:
        return abs(odds) / (abs(odds) + 100) * 100

    return 100 / (odds + 100) * 100


def expected_value(win_pct, odds):
    if pd.isna(win_pct) or pd.isna(odds):
        return np.nan

    p = win_pct / 100
    odds = float(odds)

    if odds > 0:
        return (p * odds) - ((1 - p) * 100)

    return (p * 100) - ((1 - p) * abs(odds))


def grade_play(ev, diff):
    if ev >= 20 and diff >= 10:
        return "Strong Play"
    if ev >= 10 and diff >= 5:
        return "Playable"
    if ev > 5:
        return "Lean"
    return "Pass"


def is_dog(odds):
    return not pd.isna(odds) and odds > 0


# =====================================================
# LOAD GOOGLE SHEET
# =====================================================

@st.cache_data(ttl=300)
def load_sheet():
    return pd.read_csv(SHEET_URL, header=None, dtype=str)


raw = load_sheet()


# =====================================================
# PARSE GAME ROWS
# =====================================================

def parse_games(raw_df):
    games = []

    for i in range(len(raw_df) - 1):
        row = raw_df.iloc[i]
        next_row = raw_df.iloc[i + 1]

        if clean_text(row.iloc[0]).lower() == "away" and clean_text(next_row.iloc[0]).lower() == "home":

            away_team = clean_text(row.iloc[1])
            away_nick = clean_text(row.iloc[2])
            home_team = clean_text(next_row.iloc[1])
            home_nick = clean_text(next_row.iloc[2])

            if away_team == "" or home_team == "":
                continue

            away_odds = to_odds(row.iloc[4])
            home_odds = to_odds(next_row.iloc[4])

            away_runs = to_float(row.iloc[11])
            home_runs = to_float(next_row.iloc[11])

            away_win = to_float(row.iloc[15])
            home_win = to_float(next_row.iloc[15])

            away_vegas = implied_prob(away_odds)
            home_vegas = implied_prob(home_odds)

            away_diff = away_win - away_vegas if not pd.isna(away_win) and not pd.isna(away_vegas) else np.nan
            home_diff = home_win - home_vegas if not pd.isna(home_win) and not pd.isna(home_vegas) else np.nan

            away_ev = expected_value(away_win, away_odds)
            home_ev = expected_value(home_win, home_odds)

            games.append({
                "Away Team": away_team,
                "Home Team": home_team,
                "Away Full": f"{away_team} {away_nick}".strip(),
                "Home Full": f"{home_team} {home_nick}".strip(),

                "Away Odds": away_odds,
                "Home Odds": home_odds,

                "Away Runs": away_runs,
                "Home Runs": home_runs,

                "Away Vegas Win %": away_vegas,
                "Home Vegas Win %": home_vegas,

                "Away My Win %": away_win,
                "Home My Win %": home_win,

                "Away Diff": away_diff,
                "Home Diff": home_diff,

                "Away EV": away_ev,
                "Home EV": home_ev,

                "Sharp Away": 0,
                "Sharp Home": 0,
            })

    return pd.DataFrame(games)


results_df = parse_games(raw)


# =====================================================
# PICK LOGIC
# =====================================================

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


pick_info = results_df.apply(get_pick_info, axis=1)
results_df = pd.concat([results_df, pick_info], axis=1)

results_df["Pick Grade"] = results_df.apply(
    lambda r: grade_play(r["Pick EV"], r["Pick Diff"]),
    axis=1
)


# =====================================================
# COLOR TABLE
# =====================================================

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

    if col == "Pick Grade":
        if val == "Strong Play":
            return "background:#0f9d58;color:white;font-weight:bold;"
        if val == "Playable":
            return "background:#b7e1cd;color:black;font-weight:bold;"
        if val == "Lean":
            return "background:#fff2cc;color:black;"
        return "background:#eeeeee;color:#666;"

    if col == "Pick":
        if val != "PASS":
            return "background:#0f9d58;color:white;font-weight:bold;"
        return "background:#eeeeee;color:#666;"

    return ""


def fmt_value(col, val):
    if pd.isna(val):
        return ""

    if isinstance(val, (float, int, np.integer, np.floating)):
        if "%" in col or "Diff" in col:
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


# =====================================================
# WRITEUPS
# =====================================================

def sharp_comment(team, sharp_value):
    try:
        sharp_value = float(sharp_value)
    except Exception:
        sharp_value = 0

    if sharp_value >= 20:
        return f"Strong sharp support is showing on {team}."
    if sharp_value >= 10:
        return f"Moderate sharp support is showing on {team}."
    if sharp_value <= -20:
        return f"There is heavy sharp resistance against {team}."
    if sharp_value <= -10:
        return f"There is some sharp resistance against {team}."

    return "No major sharp signal detected."


def generate_writeup(row):
    if row["Pick"] == "PASS":
        return f"""
### {row['Away Team']} vs {row['Home Team']}

**PASS**

This game does not meet the current EV and edge thresholds.

The model is not showing enough value to force a bet here.
"""

    team = row["Pick"]
    opponent = row["Home Team"] if row["Pick Side"] == "Away" else row["Away Team"]

    dog_note = (
        "This is an underdog value play. The market is pricing this team lower than your model does."
        if row["Dog Pick"]
        else "This is a favorite play with model support. The key is that the price still appears playable."
    )

    return f"""
### {row['Away Team']} vs {row['Home Team']}

## Pick: {team} ML ({int(row['Pick Odds'])})

**Grade:** {row['Pick Grade']}

### Model vs Market

- Vegas Win %: **{row['Pick Vegas Win %']:.2f}%**
- Model Win %: **{row['Pick Win %']:.2f}%**
- Difference: **{row['Pick Diff']:.2f}%**
- Expected Value: **{row['Pick EV']:.2f}**

### Read

{dog_note}

Your model prices {team} better than the market does. The edge over Vegas is **{row['Pick Diff']:.2f}%**, with an EV of **{row['Pick EV']:.2f}**.

Against {opponent}, this qualifies because both the EV and difference thresholds are met.

### Sharp Money

{sharp_comment(team, row['Pick Sharp'])}

### Risk Notes

- MLB variance is high.
- Avoid forcing every edge into a parlay.
- Strong favorites can still be overpriced.
- Underdogs carry more volatility.
"""


# =====================================================
# DISPLAY
# =====================================================

st.title("⚾ my_MLB Betting Dashboard")
st.caption("Data is pulled directly from your Google Sheet tab.")

if results_df.empty:
    st.error("No games found. Check that your Google Sheet layout still has Away/Home rows.")
    st.stop()

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
