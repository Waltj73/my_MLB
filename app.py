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


def color_board(row):
    styles = [""] * len(row)
    col = {c: i for i, c in enumerate(row.index)}

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

    for c in ["Diff Away", "Diff Home", "Pick Diff"]:
        if c in col:
            val = to_num(row[c])

            if val >= 10:
                styles[col[c]] = "background-color:#d4efdf;color:black;font-weight:bold;"
            elif val >= 5:
                styles[col[c]] = "background-color:#fff3cd;color:black;"
            elif val <= -10:
                styles[col[c]] = "background-color:#f5b7b1;color:black;"

    if "Model Pick" in col:
        if row["Model Pick"] != "PASS":
            styles[col["Model Pick"]] = "background-color:#1e8449;color:white;font-weight:bold;"
        else:
            styles[col["Model Pick"]] = "background-color:#eeeeee;color:#777;"

    if "Grade" in col:
        if row["Grade"] == "Strong Play":
            styles[col["Grade"]] = "background-color:#00a651;color:white;font-weight:bold;"
        elif row["Grade"] == "Playable":
            styles[col["Grade"]] = "background-color:#a9dfbf;color:black;font-weight:bold;"
        elif row["Grade"] == "Lean":
            styles[col["Grade"]] = "background-color:#fff3cd;color:black;"
        else:
            styles[col["Grade"]] = "background-color:#eeeeee;color:#777;"

    if "Sharp Dog" in col and str(row["Sharp Dog"]).strip() != "":
        styles[col["Sharp Dog"]] = "background-color:#d6eaf8;color:#154360;font-weight:bold;"

    if (
        "Model Pick" in row.index
        and "Sharp Dog" in row.index
        and row["Model Pick"] != "PASS"
        and str(row["Sharp Dog"]).strip() != ""
        and normalize(row["Model Pick"]) == normalize(row["Sharp Dog"])
    ):
        for i in range(len(styles)):
            if styles[i] == "":
                styles[i] = "background-color:#eef7ff;"

    return styles


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

df = df[df["Away Team"].astype(str).str.strip() != ""].copy().reset_index(drop=True)


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

# Cleaner display order
display_cols = [
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
    "Model Pick",
    "Pick Side",
    "Pick Odds",
    "Pick EV",
    "Pick Diff",
    "Grade",
]

display_cols = [c for c in display_cols if c in df.columns]

model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = model_plays.sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
).head(5)

# FIXED: this now uses the actual Sharp Dog column from your sheet
sharp_dogs = df[
    df["Sharp Dog"].astype(str).str.strip() != ""
].copy()

sharp_dogs = sharp_dogs.sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
)

# Model underdogs only
model_dogs = model_plays[
    model_plays.apply(lambda r: is_dog(r["Pick Odds"]), axis=1)
].sort_values(
    by=["Pick EV", "Pick Diff"],
    ascending=[False, False]
)

signals = model_plays[
    model_plays.apply(
        lambda r: (
            str(r["Sharp Dog"]).strip() != ""
            and normalize(r["Model Pick"]) == normalize(r["Sharp Dog"])
        ),
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

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Games", len(df))
c2.metric("Model Plays", len(model_plays))
c3.metric("Sharp Dogs", len(sharp_dogs))
c4.metric("Model Dogs", len(model_dogs))
c5.metric("Signal Plays", len(signals))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "All Games",
    "Top 5 Plays",
    "Sharp Dogs",
    "Model Underdogs",
    "Signal Plays"
])

TABLE_HEIGHT = 850

with tab1:
    st.subheader("All Games")

    st.dataframe(
        df[display_cols].style.apply(color_board, axis=1),
        use_container_width=True,
        hide_index=True,
        height=TABLE_HEIGHT
    )

with tab2:
    st.subheader("Top 5 Model Plays")

    if top_plays.empty:
        st.info("No model plays found.")
    else:
        st.dataframe(
            top_plays[display_cols].style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT
        )

with tab3:
    st.subheader("Sharp Dogs Listed In Sheet")

    if sharp_dogs.empty:
        st.info("No sharp dogs listed.")
    else:
        st.dataframe(
            sharp_dogs[display_cols].style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT
        )

with tab4:
    st.subheader("Model Underdog Plays")

    if model_dogs.empty:
        st.info("No model underdog plays found.")
    else:
        st.dataframe(
            model_dogs[display_cols].style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT
        )

with tab5:
    st.subheader("Signal Plays")

    if signals.empty:
        st.info("No sharp/model alignment plays found.")
    else:
        st.dataframe(
            signals[display_cols].style.apply(color_board, axis=1),
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT
        )
