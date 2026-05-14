import streamlit as st
import pandas as pd

st.set_page_config(page_title="MLB Command Center", layout="wide")

SHEET_ID = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
SHEET_NAME = "APP_EXPORT"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

EV_THRESHOLD = 5
DIFF_THRESHOLD = 5


@st.cache_data(ttl=30)
def load_data():
    df = pd.read_csv(URL)
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def to_num(v):
    try:
        return float(str(v).replace("%", "").replace("+", "").replace(",", "").strip())
    except Exception:
        return 0.0


def normalize(v):
    return str(v).strip().upper()


def get_pick(row):
    away_ev = to_num(row["Away EV"])
    home_ev = to_num(row["Home EV"])
    away_diff = to_num(row["Away Diff"])
    home_diff = to_num(row["Home Diff"])

    away_play = away_ev > EV_THRESHOLD and away_diff >= DIFF_THRESHOLD
    home_play = home_ev > EV_THRESHOLD and home_diff >= DIFF_THRESHOLD

    if away_play and (away_ev >= home_ev or not home_play):
        return row["Away Team"], "Away", away_ev, away_diff

    if home_play and (home_ev > away_ev or not away_play):
        return row["Home Team"], "Home", home_ev, home_diff

    return "PASS", "Pass", max(away_ev, home_ev), max(away_diff, home_diff)


def grade(ev, diff):
    if ev >= 20 and diff >= 10:
        return "Strong Play"
    if ev >= 10 and diff >= 5:
        return "Playable"
    if ev > 5:
        return "Lean"
    return "Pass"


def writeup(row):
    if row["Model Pick"] == "PASS":
        return f"""
### {row['Away Team']} @ {row['Home Team']}

**PASS**

No clean model edge. Neither side meets the EV + Diff threshold.
"""

    pick = row["Model Pick"]
    sharp = str(row.get("Sharp Dog", "")).strip()

    if normalize(pick) == normalize(sharp):
        sharp_read = "Sharp side and model pick are aligned. This is a cleaner signal."
    elif sharp:
        sharp_read = f"Sharp side points to **{sharp}**, while the model points to **{pick}**. This is a conflict spot."
    else:
        sharp_read = "No sharp dog signal listed. This is mostly a model-based play."

    return f"""
### {row['Away Team']} @ {row['Home Team']}

## Pick: {pick}

**Grade:** {row['Grade']}

### Model Edge

- Pick EV: **{row['Pick EV']:.2f}**
- Pick Diff: **{row['Pick Diff']:.2f}%**
- Sharp Dog: **{sharp if sharp else "None"}**

### Matchup Data

**{row['Away Team']}**
- Odds: {row['Away Odds']}
- Win %: {row['Away Win %']}
- Diff: {row['Away Diff']}
- EV: {row['Away EV']}

**{row['Home Team']}**
- Odds: {row['Home Odds']}
- Win %: {row['Home Win %']}
- Diff: {row['Home Diff']}
- EV: {row['Home EV']}

### Sharp / Market Read

{sharp_read}

### Final Read

This qualifies because the model side has positive EV and a meaningful difference over the market. If sharp money agrees, confidence improves. If sharp money conflicts, treat it with caution.
"""


df = load_data()

required_cols = [
    "Away Team", "Home Team",
    "Away Odds", "Home Odds",
    "Away Win %", "Home Win %",
    "Away Diff", "Home Diff",
    "Away EV", "Home EV",
    "Sharp Away", "Sharp Home", "Sharp Dog"
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing columns in APP_EXPORT: {missing}")
    st.write("Detected columns:", list(df.columns))
    st.stop()

df = df[df["Away Team"].astype(str).str.strip() != ""].copy()

picks = df.apply(get_pick, axis=1)

df["Model Pick"] = [p[0] for p in picks]
df["Pick Side"] = [p[1] for p in picks]
df["Pick EV"] = [p[2] for p in picks]
df["Pick Diff"] = [p[3] for p in picks]
df["Grade"] = df.apply(lambda r: grade(r["Pick EV"], r["Pick Diff"]), axis=1)

model_plays = df[df["Model Pick"] != "PASS"].copy()
top_plays = model_plays.sort_values(by="Pick EV", ascending=False).head(5)
dogs = model_plays[
    model_plays.apply(
        lambda r: to_num(r["Away Odds"]) > 0 if r["Pick Side"] == "Away" else to_num(r["Home Odds"]) > 0,
        axis=1
    )
].sort_values(by="Pick EV", ascending=False)

signals = model_plays[
    model_plays.apply(lambda r: normalize(r["Model Pick"]) == normalize(r["Sharp Dog"]), axis=1)
].sort_values(by="Pick EV", ascending=False)

st.title("⚾ MLB Command Center")
st.caption("Reading directly from APP_EXPORT")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "All Games",
    "Top 5 Plays",
    "Underdogs",
    "Signal Plays",
    "Writeups"
])

with tab1:
    st.subheader("All Games")
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Top 5 Model Plays")
    st.dataframe(top_plays, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Underdog Plays")
    if dogs.empty:
        st.info("No underdog plays found.")
    else:
        st.dataframe(dogs, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Signal Plays")
    if signals.empty:
        st.info("No sharp/model alignment plays found.")
    else:
        st.dataframe(signals, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Writeups")
    if model_plays.empty:
        st.info("No model plays to write up.")
    else:
        for _, row in model_plays.sort_values(by="Pick EV", ascending=False).iterrows():
            st.markdown(writeup(row))
            st.divider()
