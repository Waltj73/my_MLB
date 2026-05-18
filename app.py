import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

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

# skiprows=1 drops the top text row so your true headers become the column names
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&skiprows=1"

EV_THRESHOLD = 5
DIFF_THRESHOLD = 5


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.read_csv(URL)
        # Strip any accidental whitespace from the sheet's column headers
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


def prepare_display(df):
    cols = [
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

    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()


# ============================================================
# AGGRID TABLE WITH COLOR CODING
# ============================================================

def show_grid(df, height=825):
    display_df = prepare_display(df)

    gb = GridOptionsBuilder.from_dataframe(display_df)

    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=True,
        minWidth=110,
        wrapText=False,
        autoHeight=False,
    )

    # ----------------------------
    # PINNED COLUMNS
    # ----------------------------

    if "Away Team" in display_df.columns:
        gb.configure_column(
            "Away Team",
            pinned="left",
            width=130
        )

    if "Home Team" in display_df.columns:
        gb.configure_column(
            "Home Team",
            pinned="left",
            width=130
        )

    if "Model Pick" in display_df.columns:
        gb.configure_column(
            "Model Pick",
            pinned="right",
            width=140
        )

    if "Grade" in display_df.columns:
        gb.configure_column(
            "Grade",
            pinned="right",
            width=120
        )

    # ----------------------------
    # COLOR STYLES
    # ----------------------------

    ev_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('%','').trim());
        if (isNaN(val)) return {};
        if (val >= 20) return {backgroundColor: '#00a651', color: 'white', fontWeight: 'bold'};
        if (val >= 10) return {backgroundColor: '#7DCEA0', color: 'black', fontWeight: 'bold'};
        if (val > 0) return {backgroundColor: '#D5F5E3', color: 'black'};
        if (val < 0) return {backgroundColor: '#F5B7B1', color: 'black'};
        return {};
    }
    """)

    diff_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('%','').trim());
        if (isNaN(val)) return {};
        if (val >= 10) return {backgroundColor: '#58D68D', color: 'white', fontWeight: 'bold'};
        if (val >= 5) return {backgroundColor: '#F9E79F', color: 'black', fontWeight: 'bold'};
        if (val <= -10) return {backgroundColor: '#F1948A', color: 'black'};
        return {};
    }
    """)

    pick_style = JsCode("""
    function(params) {
        if (params.value === 'PASS') return {backgroundColor: '#EEEEEE', color: '#666666'};
        if (params.value) return {backgroundColor: '#1E8449', color: 'white', fontWeight: 'bold'};
        return {};
    }
    """)

    sharp_style = JsCode("""
    function(params) {
        if (params.value && String(params.value).trim() !== '') {
            return {backgroundColor: '#D6EAF8', color: '#154360', fontWeight: 'bold'};
        }
        return {};
    }
    """)

    grade_style = JsCode("""
    function(params) {
        if (params.value === 'Strong Play') return {backgroundColor: '#00a651', color: 'white', fontWeight: 'bold'};
        if (params.value === 'Playable') return {backgroundColor: '#A9DFBF', color: 'black', fontWeight: 'bold'};
        if (params.value === 'Lean') return {backgroundColor: '#FCF3CF', color: 'black', fontWeight: 'bold'};
        if (params.value === 'Pass') return {backgroundColor: '#EEEEEE', color: '#666666'};
        return {};
    }
    """)

    odds_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('+','').trim());
        if (isNaN(val)) return {};
        if (val > 0) return {backgroundColor: '#EBF5FB', color: '#154360', fontWeight: 'bold'};
        if (val < 0) return {backgroundColor: '#FDEDEC', color: '#922B21', fontWeight: 'bold'};
        return {};
    }
    """)

    signal_row_style = JsCode("""
    function(params) {
        let pick = params.data["Model Pick"];
        let sharp = params.data["Sharp Dog"];
        if (pick && sharp && pick !== "PASS" && String(pick).trim().toUpperCase() === String(sharp).trim().toUpperCase()) {
            return {backgroundColor: '#EEF7FF'};
        }
        return {};
    }
    """)

    # ----------------------------
    # APPLY COLUMN STYLES
    # ----------------------------

    for col in ["EV Away", "EV Home", "Pick EV"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=ev_style)

    for col in ["Diff Away", "Diff Home", "Pick Diff"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=diff_style)

    for col in ["Away Odds", "Home Odds", "Pick Odds"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=odds_style)

    if "Sharp Dog" in display_df.columns:
        gb.configure_column("Sharp Dog", width=125, cellStyle=sharp_style)

    if "Model Pick" in display_df.columns:
        gb.configure_column("Model Pick", pinned="right", width=140, cellStyle=pick_style)

    if "Grade" in display_df.columns:
        gb.configure_column("Grade", pinned="right", width=120, cellStyle=grade_style)

    for col in ["Sharp Away", "Sharp Home", "Vegas Win Away", "Vegas Win Home", "My Win Away", "My Win Home"]:
        if col in display_df.columns:
            gb.configure_column(col, width=125)

    grid_options = gb.build()
    grid_options["getRowStyle"] = signal_row_style

    AgGrid(
        display_df,
        gridOptions=grid_options,
        height=height,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        theme="balham",
        enable_enterprise_modules=False,
    )


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

# Clean out any empty rows below the true data payload
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


# ============================================================
# FILTERS / DATASETS
# ============================================================

model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = pd.DataFrame()
if not model_plays.empty:
    top_plays = model_plays.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False]).head(5)

sharp_dogs = df[df["Sharp Dog"].astype(str).str.strip() != ""].copy()
if not sharp_dogs.empty:
    sharp_dogs = sharp_dogs.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])

model_dogs = pd.DataFrame()
if not model_plays.empty:
    model_dogs = model_plays[model_plays.apply(lambda r: is_dog(r["Pick Odds"]), axis=1)].copy()
    if not model_dogs.empty:
        model_dogs = model_dogs.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])

signals = pd.DataFrame()
if not model_plays.empty:
    signals = model_plays[
        model_plays.apply(
            lambda r: (str(r["Sharp Dog"]).strip() != "" and normalize(r["Model Pick"]) == normalize(r["Sharp Dog"])),
            axis=1
        )
    ].copy()
    if not signals.empty:
        signals = signals.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])


# ============================================================
# DISPLAY
# ============================================================

st.title("⚾ MLB Command Center")
st.caption("Spreadsheet-style betting board powered by APP_EXPORT")

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
    "Model Dogs",
    "Signal Plays"
])

with tab1:
    st.subheader("All Games")
    show_grid(df, height=850)

with tab2:
    st.subheader("Top 5 Model Plays")
    if top_plays.empty:
        st.info("No model plays found.")
    else:
        show_grid(top_plays, height=500)

with tab3:
    st.subheader("Sharp Dogs Listed In Sheet")
    if sharp_dogs.empty:
        st.info("No sharp dogs listed.")
    else:
        show_grid(sharp_dogs, height=850)

with tab4:
    st.subheader("Model Underdog Plays")
    if model_dogs.empty:
        st.info("No model underdog plays found.")
    else:
        show_grid(model_dogs, height=850)

with tab5:
    st.subheader("Signal Plays")
    if signals.empty:
        st.info("No sharp/model alignment plays found.")
    else:
        show_grid(signals, height=850)
