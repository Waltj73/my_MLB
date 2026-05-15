import streamlit as st
import pandas as pd

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MLB Command Center",
    layout="wide"
)

# ============================================================
# GOOGLE SHEET SETTINGS
# ============================================================

SHEET_ID = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
SHEET_NAME = "APP_EXPORT"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

EV_THRESHOLD = 5
DIFF_THRESHOLD = 5
HIGH_EV_THRESHOLD = 10


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = [str(c).strip() for c in df.columns]
        return df.fillna("")
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()


# ============================================================
# HELPERS
# ============================================================

def to_num(v):
    try:
        return float(
            str(v)
            .replace("%", "")
            .replace("+", "")
            .replace(",", "")
            .strip()
        )
    except Exception:
        return 0.0


def normalize(v):
    return str(v).strip().upper()


def is_dog(odds):
    return to_num(odds) > 0


def edge_tier(ev):
    ev = to_num(ev)

    if ev >= 20:
        return "🟢 Elite Edge"
    if ev >= 15:
        return "🔵 Strong Edge"
    if ev >= 10:
        return "🟡 Value Edge"
    if ev >= 5:
        return "⚪ Small Edge"

    return "No Edge"


def get_pick(row):
    away_ev = to_num(row["EV Away"])
    home_ev = to_num(row["EV Home"])

    away_diff = to_num(row["Diff Away"])
    home_diff = to_num(row["Diff Home"])

    away_play = away_ev > EV_THRESHOLD and away_diff >= DIFF_THRESHOLD
    home_play = home_ev > EV_THRESHOLD and home_diff >= DIFF_THRESHOLD

    if away_play and (away_ev >= home_ev or not home_play):
        return row["Away Team"], "Away", away_ev, away_diff, row["Away Odds"]

    if home_play and (home_ev > away_ev or not away_play):
        return row["Home Team"], "Home", home_ev, home_diff, row["Home Odds"]

    return "PASS", "Pass", max(away_ev, home_ev), max(away_diff, home_diff), ""


def grade_play(ev, diff):
    ev = to_num(ev)
    diff = to_num(diff)

    if ev >= 20 and diff >= 10:
        return "Strong Play"
    if ev >= 10 and diff >= 5:
        return "Playable"
    if ev > 5:
        return "Lean"

    return "Pass"


def sharp_read(row):
    pick = row["Model Pick"]
    sharp_dog = str(row["Sharp Dog"]).strip()

    if pick == "PASS":
        return "No model pick."

    if sharp_dog == "":
        return "No sharp dog listed."

    if normalize(pick) == normalize(sharp_dog):
        return "Sharp side and model pick are aligned."

    return f"Sharp side points to {sharp_dog}, while the model points to {pick}. Conflict spot."


# ============================================================
# COLOR CODING
# ============================================================

def color_board(row):
    styles = [""] * len(row)
    col = {c: i for i, c in enumerate(row.index)}

    # EV columns
    for c in ["EV Away", "EV Home", "Pick EV"]:
        if c in col:
            val = to_num(row[c])

            if val >= 20:
                styles[col[c]] = "background-color:#00a651;color:white;font-weight:bold;"
            elif val >= 10:
                styles[col[c]] = "background-color:#a9dfbf;color:black;font-weight:bold;"
            elif val > 0:
                styles[col[c]] = "background-color:#e8f8f5;color:black;"
            elif val < 0:
                styles[col[c]] = "background-color:#f5b7b1;color:black;"

    # Diff columns
    for c in ["Diff Away", "Diff Home", "Pick Diff"]:
        if c in col:
            val = to_num(row[c])

            if val >= 10:
                styles[col[c]] = "background-color:#d4efdf;color:black;font-weight:bold;"
            elif val >= 5:
                styles[col[c]] = "background-color:#fff3cd;color:black;"
            elif val <= -10:
                styles[col[c]] = "background-color:#f5b7b1;color:black;"

    # Model Pick
    if "Model Pick" in col:
        if row["Model Pick"] != "PASS":
            styles[col["Model Pick"]] = "background-color:#1e8449;color:white;font-weight:bold;"
        else:
            styles[col["Model Pick"]] = "background-color:#eeeeee;color:#777;"

    # Grade
    if "Grade" in col:
        if row["Grade"] == "Strong Play":
            styles[col["Grade"]] = "background-color:#00a651;color:white;font-weight:bold;"
        elif row["Grade"] == "Playable":
            styles[col["Grade"]] = "background-color:#a9dfbf;color:black;font-weight:bold;"
        elif row["Grade"] == "Lean":
            styles[col["Grade"]] = "background-color:#fff3cd;color:black;"
        else:
            styles[col["Grade"]] = "background-color:#eeeeee;color:#777;"

    # Sharp Dog
    if "Sharp Dog" in col:
        if str(row["Sharp Dog"]).strip() != "":
            styles[col["Sharp Dog"]] = "background-color:#d6eaf8;color:#154360;font-weight:bold;"

    # Signal row: model pick matches sharp dog
    if (
        "Model Pick" in row.index
        and "Sharp Dog" in row.index
        and row["Model Pick"] != "PASS"
        and normalize(row["Model Pick"]) == normalize(row["Sharp Dog"])
    ):
        for i in range(len(styles)):
            if styles[i] == "":
                styles[i] = "background-color:#eef7ff;"

    return styles


# ============================================================
# WRITEUPS
# ============================================================

def writeup(row):
    if row["Model Pick"] == "PASS":
        return f"""
### {row['Away Team']} @ {row['Home Team']}

**PASS**

No clean model edge. Neither side meets both thresholds:

- EV > {EV_THRESHOLD}
- Diff >= {DIFF_THRESHOLD}

This is a skip unless you have outside matchup information that strongly changes the read.
"""

    pick = row["Model Pick"]
    side = row["Pick Side"]
    odds = row["Pick Odds"]
    ev = row["Pick EV"]
    diff = row["Pick Diff"]
    grade = row["Grade"]
    sharp_dog = str(row["Sharp Dog"]).strip()

    if side == "Away":
        opponent = row["Home Team"]
        win_pct = row["My Win Away"]
        vegas_pct = row["Vegas Win Away"]
        sharp_ml = row["Sharp Away"]
        opponent_ev = row["EV Home"]
        opponent_diff = row["Diff Home"]
    else:
        opponent = row["Away Team"]
        win_pct = row["My Win Home"]
        vegas_pct = row["Vegas Win Home"]
        sharp_ml = row["Sharp Home"]
        opponent_ev = row["EV Away"]
        opponent_diff = row["Diff Away"]

    dog_note = "underdog value play" if is_dog(odds) else "favorite value play"

    return f"""
### {row['Away Team']} @ {row['Home Team']}

## Pick: {pick} ML ({odds})

**Grade:** {grade}  
**Type:** {dog_note}  
**Tier:** {edge_tier(ev)}

---

### Model vs Market

- Model Win %: **{win_pct}**
- Vegas Win %: **{vegas_pct}**
- Difference: **{diff:.2f}%**
- Expected Value: **{ev:.2f}**
- Opponent EV: **{opponent_ev}**
- Opponent Diff: **{opponent_diff}**

---

### Why This Is a Play

Your sheet is showing value on **{pick}** because that side clears your minimum requirements:

- EV is above **{EV_THRESHOLD}**
- Diff is at least **{DIFF_THRESHOLD}**
- The opposing side does not grade better by your model

Against **{opponent}**, this is not just a “who wins” pick. It is a pricing play. Your numbers suggest the market is not fully accounting for the win probability your model gives to **{pick}**.

---

### Sharp / Market Read

- Sharp Dog: **{sharp_dog if sharp_dog else "None"}**
- Pick Sharp ML: **{sharp_ml}**
- Read: **{sharp_read(row)}**

If the sharp dog agrees with your model pick, confidence improves.  
If the sharp dog conflicts with your model pick, this becomes a caution spot even if EV is positive.

---

### Final Read

This qualifies as a **{grade}**.

Best use:
- Straight bet first
- Smaller sizing if sharp data conflicts
- Be careful using it as a parlay leg if the price is heavy
"""


# ============================================================
# LOAD + VALIDATE
# ============================================================

df = load_data()

if df.empty:
    st.stop()

required_cols = [
    "Away Team",
    "Home Team",
    "Away Odds",
    "Home Odds",
    "Sharp Away",
    "Sharp Home",
    "Sharp Dog",
    "Vegas Win Away",
    "Vegas Win Home",
    "My Win Away",
    "My Win Home",
    "Diff Away",
    "Diff Home",
    "EV Away",
    "EV Home",
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing columns in APP_EXPORT: {missing}")
    st.write("Detected columns:")
    st.write(list(df.columns))
    st.stop()

df = df[df["Away Team"].astype(str).str.strip() != ""].copy()


# ============================================================
# BUILD MODEL FIELDS
# ============================================================

picks = df.apply(get_pick, axis=1)

df["Model Pick"] = [p[0] for p in picks]
df["Pick Side"] = [p[1] for p in picks]
df["Pick EV"] = [p[2] for p in picks]
df["Pick Diff"] = [p[3] for p in picks]
df["Pick Odds"] = [p[4] for p in picks]

df["Grade"] = df.apply(
    lambda r: grade_play(r["Pick EV"], r["Pick Diff"]),
    axis=1
)

model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = model_plays.sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
).head(5)

dogs = model_plays[
    model_plays.apply(lambda r: is_dog(r["Pick Odds"]), axis=1)
].sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
)

signals = model_plays[
    model_plays.apply(
        lambda r: normalize(r["Model Pick"]) == normalize(r["Sharp Dog"]),
        axis=1
    )
].sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
)


# ============================================================
# DISPLAY
# ============================================================

st.title("⚾ MLB Command Center")
st.caption("Reading directly from APP_EXPORT")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Games", len(df))
c2.metric("Model Plays", len(model_plays))
c3.metric("Underdogs", len(dogs))
c4.metric("Signal Plays", len(signals))

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "All Games",
    "Top 5 Plays",
    "Underdogs",
    "Signal Plays",
    "Writeups",
    "Sharp Reads"
])

with tab1:
    st.subheader("All Games")
    st.dataframe(
        df.style.apply(color_board, axis=1),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Top 5 Model Plays")

    if top_plays.empty:
        st.info("No model plays found.")
    else:
        st.dataframe(
            top_plays.style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True
        )

with tab3:
    st.subheader("Underdog Plays")

    if dogs.empty:
        st.info("No underdog plays found.")
    else:
        st.dataframe(
            dogs.style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True
        )

with tab4:
    st.subheader("Signal Plays")

    if signals.empty:
        st.info("No sharp/model alignment plays found.")
    else:
        st.dataframe(
            signals.style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True
        )

with tab5:
    st.subheader("Writeups")

    if model_plays.empty:
        st.info("No model plays to write up.")
    else:
        for _, row in model_plays.sort_values(by="Pick EV", ascending=False).iterrows():
            st.markdown(writeup(row))
            st.divider()

with tab6:
    st.subheader("Sharp Reads")

    for _, row in df.iterrows():
        if str(row["Sharp Dog"]).strip() == "":
            continue

        st.markdown(
            f"""
### {row['Away Team']} @ {row['Home Team']}

**Sharp Dog:** {row['Sharp Dog']}  
**Model Pick:** {row['Model Pick']}  
**Read:** {sharp_read(row)}

---
"""
        )
