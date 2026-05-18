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


# ============================================================
# LOAD DATA (ONE ROW PER GAME EXTRACTED FROM TWO-ROW SHEET)
# ============================================================

@st.cache_data(ttl=30)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = [str(c).strip() for c in raw_df.columns]
        raw_df = raw_df.fillna("")
        
        # Determine the primary team column header
        team_col = "Away Team" if "Away Team" in raw_df.columns else ("Teams" if "Teams" in raw_df.columns else "")
        if not team_col:
            return pd.DataFrame()
            
        # Filter out empty formatting lines
        raw_df = raw_df[raw_df[team_col].astype(str).str.strip() != ""].reset_index(drop=True)
            
        processed_rows = []
        
        # Iterate in pairs: row i is Away, row i+1 is Home
        for i in range(0, len(raw_df), 2):
            if i + 1 >= len(raw_df):
                break
                
            away_row = raw_df.iloc[i]
            home_row = raw_df.iloc[i+1]
            
            # Handle pandas duplicate column suffix naming (.1)
            vegas_odds_away = away_row.get("Vegas Odds", 0)
            vegas_odds_home = home_row.get("Vegas Odds.1", home_row.get("Vegas Odds", 0))

            my_odds_away = away_row.get("My Odds", 0)
            my_odds_home = home_row.get("My Odds.1", home_row.get("My Odds", 0))

            sharp_ml_away = away_row.get("Sharps ML", 0)
            sharp_ml_home = home_row.get("Sharps ML.1", home_row.get("Sharps ML", 0))

            vegas_win_away = away_row.get("Vegas Win%", 0)
            vegas_win_home = home_row.get("Vegas Win%.1", home_row.get("Vegas Win%", 0))

            my_win_away = away_row.get("My Win%", 0)
            my_win_home = home_row.get("My Win%.1", home_row.get("My Win%", 0))

            diff_away = away_row.get("Differences", 0)
            diff_home = home_row.get("Differences.1", home_row.get("Differences", 0))

            ev_away = away_row.get("EV", 0)
            ev_home = home_row.get("EV.1", home_row.get("EV", 0))

            pick_away = away_row.get("Picks", "")
            pick_home = home_row.get("Picks.1", home_row.get("Picks", ""))
            
            # Determine the active model pick from columns Y and Z
            model_pick = "PASS"
            if str(pick_away).strip() != "":
                model_pick = str(pick_away).strip()
            elif str(pick_home).strip() != "":
                model_pick = str(pick_home).strip()

            game_dict = {
                "Away Team":      away_row[team_col],
                "Home Team":      home_row[team_col],
                "Away Odds":      vegas_odds_away,
                "Home Odds":      vegas_odds_home,
                "My Odds Away":   my_odds_away,
                "My Odds Home":   my_odds_home,
                "Sharp Away":     sharp_ml_away,
                "Sharp Home":     sharp_ml_home,
                "Sharp Dog":      away_row.get("Sharp Dogs", away_row.get("Sharp", "")),
                "Vegas Win Away": vegas_win_away,
                "Vegas Win Home": vegas_win_home,
                "My Win Away":    my_win_away,
                "My Win Home":    my_win_home,
                "Diff Away":      diff_away,
                "Diff Home":      diff_home,
                "EV Away":        ev_away,
                "EV Home":        ev_home,
                "Model Pick":     model_pick
            }
            processed_rows.append(game_dict)
            
        return pd.DataFrame(processed_rows)
        
    except Exception as e:
        st.error(f"Sync Parser Error: {e}")
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


def grade_play(pick, df_row):
    if str(pick).upper() == "PASS":
        return "Lean"
        
    # Read calculations directly mapped from the spreadsheet values
    if normalize(pick) == normalize(df_row["Away Team"]):
        ev = to_num(df_row["EV Away"])
        diff = to_num(df_row["Diff Away"])
    else:
        ev = to_num(df_row["EV Home"])
        diff = to_num(df_row["Diff Home"])
        
    if ev >= 20 and diff >= 10:
        return "Strong Play"
    return "Playable"


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
        "Model Pick",
        "Grade",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()


# ============================================================
# AGGRID DISPLAY COMPONENT
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

    if "Away Team" in display_df.columns:
        gb.configure_column("Away Team", pinned="left", width=130)

    if "Home Team" in display_df.columns:
        gb.configure_column("Home Team", pinned="left", width=130)

    if "Model Pick" in display_df.columns:
        gb.configure_column("Model Pick", pinned="right", width=140)

    if "Grade" in display_df.columns:
        gb.configure_column("Grade", pinned="right", width=120)

    # REPLICATED DESIGN STYLING PATTERNS
    ev_style = JsCode("""
    function(params) {
        if (params.value >= 20) return {backgroundColor: '#00a651', color: 'white', fontWeight: 'bold'};
        if (params.value >= 10) return {backgroundColor: '#7DCEA0', color: 'black', fontWeight: 'bold'};
        if (params.value > 0) return {backgroundColor: '#D5F5E3', color: 'black'};
        if (params.value < 0) return {backgroundColor: '#F5B7B1', color: 'black'};
        return {};
    }
    """)

    diff_style = JsCode("""
    function(params) {
        if (params.value >= 10) return {backgroundColor: '#58D68D', color: 'white', fontWeight: 'bold'};
        if (params.value >= 5) return {backgroundColor: '#F9E79F', color: 'black', fontWeight: 'bold'};
        if (params.value <= -10) return {backgroundColor: '#F1948A', color: 'black'};
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
        if (params.value) return {backgroundColor: '#D6EAF8', color: '#154360', fontWeight: 'bold'};
        return {};
    }
    """)

    grade_style = JsCode("""
    function(params) {
        if (params.value === 'Strong Play') return {backgroundColor: '#00a651', color: 'white', fontWeight: 'bold'};
        if (params.value === 'Playable') return {backgroundColor: '#A9DFBF', color: 'black', fontWeight: 'bold'};
        if (params.value === 'Lean') return {backgroundColor: '#FCF3CF', color: 'black', fontWeight: 'bold'};
        return {};
    }
    """)

    odds_style = JsCode("""
    function(params) {
        if (params.value > 0) return {backgroundColor: '#EBF5FB', color: '#154360', fontWeight: 'bold'};
        if (params.value < 0) return {backgroundColor: '#FDEDEC', color: '#922B21', fontWeight: 'bold'};
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

    for col in ["EV Away", "EV Home"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=ev_style)

    for col in ["Diff Away", "Diff Home"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=diff_style)

    for col in ["Away Odds", "Home Odds"]:
        if col in display_df.columns:
            gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=odds_style)

    if "Sharp Dog" in display_df.columns:
        gb.configure_column("Sharp Dog", width=125, cellStyle=sharp_style)

    if "Model Pick" in display_df.columns:
        gb.configure_column("Model Pick", pinned="right", width=140, cellStyle=pick_style)

    if "Grade" in display_df.columns:
        gb.configure_column("Grade", pinned="right", width=120, cellStyle=grade_style)

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

# Assign grades dynamically matching the sheet criteria row calculations
df["Grade"] = df.apply(lambda r: grade_play(r["Model Pick"], r), axis=1)

# Generate exact operational tracking views
model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = pd.DataFrame()
if not model_plays.empty:
    top_plays = model_plays.sort_values(by=["Grade", "Away Team"], ascending=[False, True]).head(5)

sharp_dogs = pd.DataFrame()
if "Sharp Dog" in df.columns:
    sharp_dogs = df[df["Sharp Dog"].astype(str).str.strip() != ""].copy()

model_dogs = pd.DataFrame()
if not model_plays.empty:
    def check_dog_pick(r):
        is_away = normalize(r["Model Pick"]) == normalize(r["Away Team"])
        odds_val = r["Away Odds"] if is_away else r["Home Odds"]
        return is_dog(odds_val)
    model_dogs = model_plays[model_plays.apply(check_dog_pick, axis=1)].copy()

signals = pd.DataFrame()
if not model_plays.empty and "Sharp Dog" in df.columns:
    signals = model_plays[
        model_plays.apply(
            lambda r: (str(r["Sharp Dog"]).strip() != "" and normalize(r["Model Pick"]) == normalize(r["Sharp Dog"])),
            axis=1
        )
    ].copy()


# ============================================================
# LAYOUT RENDERING
# ============================================================

st.title("⚾ MLB Command Center")
st.caption("Synchronized single-row analytics board matching spreadsheet logic.")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Games Tracked", len(df))
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
    st.subheader("All Games Master Board")
    show_grid(df, height=850)

with tab2:
    st.subheader("Top Model Edge Opportunities")
    if top_plays.empty:
        st.info("No active edge targets identified.")
    else:
        show_grid(top_plays, height=500)

with tab3:
    st.subheader("Sharp Dogs Input Track")
    if sharp_dogs.empty:
        st.info("No sharp dogs currently marked.")
    else:
        show_grid(sharp_dogs, height=850)

with tab4:
    st.subheader("Model Underdog Selections")
    if model_dogs.empty:
        st.info("No plus-money positions found.")
    else:
        show_grid(model_dogs, height=850)

with tab5:
    st.subheader("Convergence Signals")
    if signals.empty:
        st.info("No system-aligned positions found.")
    else:
        show_grid(signals, height=850)
