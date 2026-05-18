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
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

EV_THRESHOLD = 5
DIFF_THRESHOLD = 5

# ============================================================
# LOAD & TRANSFORM TWO-ROW BLOCKS TO SINGLE GAME ROWS
# ============================================================
@st.cache_data(ttl=30)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = [str(c).strip() for c in raw_df.columns]
        raw_df = raw_df.fillna("")
        
        # Strip out completely empty spacer rows if any exist
        raw_df = raw_df[raw_df["Away Team"].astype(str).str.strip() != ""].reset_index(drop=True)
        
        processed_rows = []
        
        # Loop through the spreadsheet in steps of 2 (Row 0 = Away, Row 1 = Home)
        for i in range(0, len(raw_df), 2):
            if i + 1 >= len(raw_df):
                break # Protection against trailing odd rows
                
            away_row = raw_df.iloc[i]
            home_row = raw_df.iloc[i+1]
            
            # Map stacked rows to single-row layout expected by app metrics
            game_dict = {
                "Away Team":      away_row["Away Team"],
                "Home Team":      home_row["Home Team"],
                "Away Odds":      away_row["Vegas Odds"],
                "Home Odds":      home_row["Vegas Odds.1"] if "Vegas Odds.1" in raw_df.columns else home_row["Vegas Odds"],
                "Sharp Away":     away_row["Sharps ML"],
                "Sharp Home":     home_row["Sharps ML"],
                "Sharp Dog":      away_row["Sharp"] if "Sharp" in raw_df.columns else away_row.get("Sharp Dog", ""),
                "Vegas Win Away": away_row["Vegas Win%"],
                "Vegas Win Home": home_row["Vegas Win%"],
                "My Win Away":    away_row["My Win%"],
                "My Win Home":    home_row["My Win%"],
                "Diff Away":      away_row["Differences"],
                "Diff Home":      home_row["Differences"],
                "EV Away":        away_row["EV"],
                "EV Home":        home_row["EV"]
            }
            processed_rows.append(game_dict)
            
        return pd.DataFrame(processed_rows)
        
    except Exception as e:
        st.error(f"Sync/Parser Error: {e}")
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
        "Away Team", "Home Team", "Away Odds", "Home Odds",
        "Sharp Away", "Sharp Home", "Sharp Dog",
        "Vegas Win Away", "Vegas Win Home", "My Win Away", "My Win Home",
        "Diff Away", "Diff Home", "EV Away", "EV Home",
        "Model Pick", "Pick Side", "Pick Odds", "Pick EV", "Pick Diff", "Grade"
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()

# ============================================================
# AGGRID TABLE WITH COLOR CODING
# ============================================================
def show_grid(display_df, height=825):
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True, minWidth=110, wrapText=False, autoHeight=False
    )

    if "Away Team" in display_df.columns:
        gb.configure_column("Away Team", pinned="left", width=130)
    if "Home Team" in display_df.columns:
        gb.configure_column("Home Team", pinned="left", width=130)
    if "Model Pick" in display_df.columns:
        gb.configure_column("Model Pick", pinned="right", width=140)
    if "Grade" in display_df.columns:
        gb.configure_column("Grade", pinned="right", width=120)

    # JS Component Styles
    ev_style = JsCode("""
    function(params) {
        if (params.value >= 20) return { backgroundColor: '#00a651', color: 'white', fontWeight: 'bold' };
        if (params.value >= 10) return { backgroundColor: '#7DCEA0', color: 'black', fontWeight: 'bold' };
        if (params.value > 0) return { backgroundColor: '#D5F5E3', color: 'black' };
        if (params.value < 0) return { backgroundColor: '#F5B7B1', color: 'black' };
        return {};
    }""")

    diff_style = JsCode("""
    function(params) {
        if (params.value >= 10) return { backgroundColor: '#58D68D', color: 'white', fontWeight: 'bold' };
        if (params.value >= 5) return { backgroundColor: '#F9E79F', color: 'black', fontWeight: 'bold' };
        if (params.value <= -10) return { backgroundColor: '#F1948A', color: 'black' };
        return {};
    }""")

    pick_style = JsCode("""
    function(params) {
        if (params.value === 'PASS') return { backgroundColor: '#EEEEEE', color: '#666666' };
        if (params.value) return { backgroundColor: '#1E8449', color: 'white', fontWeight: 'bold' };
        return {};
    }""")

    sharp_style = JsCode("""
    function(params) {
        if (params.value) return { backgroundColor: '#D6EAF8', color: '#154360', fontWeight: 'bold' };
        return {};
    }""")

    grade_style = JsCode("""
    function(params) {
        if (params.value === 'Strong Play') return { backgroundColor: '#00a651', color: 'white', fontWeight: 'bold' };
        if (params.value === 'Playable') return { backgroundColor: '#A9DFBF', color: 'black', fontWeight: 'bold' };
        if (params.value === 'Lean') return { backgroundColor: '#FCF3CF', color: 'black', fontWeight: 'bold' };
        if (params.value === 'Pass') return { backgroundColor: '#EEEEEE', color: '#666666' };
        return {};
    }""")

    odds_style = JsCode("""
    function(params) {
        if (params.value > 0) return { backgroundColor: '#EBF5FB', color: '#154360', fontWeight: 'bold' };
        if (params.value < 0) return { backgroundColor: '#FDEDEC', color: '#922B21', fontWeight: 'bold' };
        return {};
    }""")

    signal_row_style = JsCode("""
    function(params) {
        let pick = params.data["Model Pick"];
        let sharp = params.data["Sharp Dog"];
        if (pick && sharp && pick !== "PASS" && String(pick).trim().toUpperCase() === String(sharp).trim().toUpperCase()) {
            return { backgroundColor: '#EEF7FF' };
        }
        return {};
    }""")

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
# EXECUTION PIPELINE
# ============================================================
df = load_data()

if df.empty:
    st.stop()

# Build processing fields on the unified single-row representation
picks = df.apply(get_pick, axis=1)

df["Model Pick"] = [p[0] for p in picks]
df["Pick Side"] = [p[1] for p in picks]
df["Pick EV"] = [p[2] for p in picks]
df["Pick Diff"] = [p[3] for p in picks]
df["Pick Odds"] = [p[4] for p in picks]

df["Grade"] = df.apply(lambda r: grade_play(r["Pick EV"], r["Pick Diff"]), axis=1)

# ============================================================
# FILTERS / DATASETS
# ============================================================
model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = model_plays.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False]).head(5)

sharp_dogs = df[df["Sharp Dog"].astype(str).str.strip() != ""].copy().sort_values(
    by=["Pick EV", "Pick Diff"], ascending=[False, False]
)

model_dogs = model_plays[model_plays.apply(lambda r: is_dog(r["Pick Odds"]), axis=1)].copy().sort_values(
    by=["Pick EV", "Pick Diff"], ascending=[False, False]
)

signals = model_plays[
    model_plays.apply(
        lambda r: (str(r["Sharp Dog"]).strip() != "" and normalize(r["Model Pick"]) == normalize(r["Sharp Dog"])),
        axis=1
    )
].copy().sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])

# ============================================================
# DISPLAY DASHBOARD UI
# ============================================================
st.title("⚾ MLB Command Center")
st.caption("Unified single-row betting board matched flawlessly from APP_EXPORT")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Games", len(df))
c2.metric("Model Plays", len(model_plays))
c3.metric("Sharp Dogs", len(sharp_dogs))
c4.metric("Model Dogs", len(model_dogs))
c5.metric("Signal Plays", len(signals))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "All Games", "Top 5 Plays", "Sharp Dogs", "Model Dogs", "Signal Plays"
])

with tab1:
    st.subheader("All Games Layout")
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
