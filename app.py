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

# skiprows=1 skips the merged top headers (Teams, Vegas Odds, etc.)
# This forces Row 2 (Away Team, Home Team, Away, Home) to be the literal column names.
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&skiprows=1"


# ============================================================
# LOAD DATA & DYNAMIC DUPLICATE COLUMN MAPPING
# ============================================================

@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # Strip whitespace clean from headers
        df.columns = [str(c).strip() for c in df.columns]
        
        # Filter out empty formatting lines or trailing summary rows
        if "Away Team" in df.columns:
            df = df[df["Away Team"].astype(str).str.strip() != ""]
            df = df[~df["Away Team"].astype(str).str.contains("Away Team|Teams", case=False)]
            
        return df.fillna("").reset_index(drop=True)
        
    except Exception as e:
        st.error(f"Sync Connection Error: {e}")
        return pd.DataFrame()


# ============================================================
# CALCULATIONS & HELPERS
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


def get_model_pick(row):
    # Pandas automatically adds duplicates as Name.1, Name.2, etc. moving left-to-right.
    # Col Y & Z ("Picks" block -> Away / Home subheaders) resolve to "Away.2" and "Home.2"
    p_away = str(row.get("Away.2", row.get("Away", ""))).strip()
    p_home = str(row.get("Home.2", row.get("Home", ""))).strip()

    if p_away and p_away.upper() != "NAN" and p_away != "0" and p_away != "0.0":
        return p_away
    if p_home and p_home.upper() != "NAN" and p_home != "0" and p_home != "0.0":
        return p_home
    return "PASS"


def grade_play(pick, row):
    if str(pick).upper() == "PASS":
        return "Lean"
        
    # Col W & X ("EV" block -> Away / Home subheaders) resolve to "Away.1" and "Home.1"
    # Col U & V ("Differences" block) map here dynamically based on the pick team alignment
    if normalize(pick) == normalize(row.get("Away Team", "")):
        ev = to_num(row.get("Away.1", 0.0))
        diff = to_num(row.get("Away", 0.0))  # Fallback check if index structure shifts
    else:
        ev = to_num(row.get("Home.1", 0.0))
        diff = to_num(row.get("Home", 0.0))

    if ev >= 20:
        return "Strong Play"
    if ev >= 10:
        return "Playable"
    return "Lean"


def prepare_display(df):
    # Map the parsed Pandas duplicate columns directly to your clean UI display matrix
    display_df = pd.DataFrame()
    
    display_df["Away Team"] = df["Away Team"]
    display_df["Home Team"] = df["Home Team"]
    
    # Vegas Odds (Cols E & F) -> Native "Away" & "Home"
    display_df["Away Odds"] = df["Away"]
    display_df["Home Odds"] = df["Home"]
    
    # Sharps ML (Cols N & O) -> First duplicates "Away.1" & "Home.1"
    # If your sheet doesn't contain Sharps ML, these handles catch gracefully
    if "Away.1" in df.columns: display_df["Sharp Away"] = df["Away.1"]
    if "Home.1" in df.columns: display_df["Sharp Home"] = df["Home.1"]
    
    # Sharp Dogs (Col P) -> Maps to "Dogs" or "Sharp" depending on parse read
    if "Dogs" in df.columns: display_df["Sharp Dog"] = df["Dogs"]
    elif "Sharp" in df.columns: display_df["Sharp Dog"] = df["Sharp"]
    
    # Append App Calculation Matrix Fields 
    if "Model Pick" in df.columns: display_df["Model Pick"] = df["Model Pick"]
    if "Grade" in df.columns: display_df["Grade"] = df["Grade"]
    
    return display_df


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

    gb.configure_column("Away Team", pinned="left", width=130)
    gb.configure_column("Home Team", pinned="left", width=130)
    gb.configure_column("Model Pick", pinned="right", width=140)
    gb.configure_column("Grade", pinned="right", width=120)

    # UI DESIGN COLOR STYLING 
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

    pick_style = JsCode("""
    function(params) {
        if (!params.value || params.value === 'PASS') return {backgroundColor: '#EEEEEE', color: '#666666'};
        return {backgroundColor: '#1E8449', color: 'white', fontWeight: 'bold'};
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

    for col in ["Away Odds", "Home Odds"]:
        if col in display_df.columns:
            gb.configure_column(col, cellStyle=odds_style)

    if "Sharp Dog" in display_df.columns: gb.configure_column("Sharp Dog", cellStyle=sharp_style)
    if "Model Pick" in display_df.columns: gb.configure_column("Model Pick", cellStyle=pick_style)
    if "Grade" in display_df.columns: gb.configure_column("Grade", cellStyle=grade_style)

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
# RUN PROCESSING PIPELINE
# ============================================================

df = load_data()

if df.empty:
    st.error("Data Sync Failure. Verify source spreadsheet structural headers.")
    st.stop()

# Map the programmatic outputs down rows sequentially
df["Model Pick"] = df.apply(get_model_pick, axis=1)
df["Grade"] = df.apply(lambda r: grade_play(r["Model Pick"], r), axis=1)

# Generate subsets for dashboard tab routing
model_plays = df[df["Model Pick"] != "PASS"].copy()

top_plays = pd.DataFrame()
if not model_plays.empty:
    top_plays = model_plays.sort_values(by=["Grade", "Away Team"], ascending=[False, True]).head(5)

sharp_dogs = pd.DataFrame()
sharp_col = "Dogs" if "Dogs" in df.columns else "Sharp"
if sharp_col in df.columns:
    sharp_dogs = df[df[sharp_col].astype(str).str.strip() != ""].copy()

model_dogs = pd.DataFrame()
if not model_plays.empty:
    def check_dog_pick(r):
        is_away = normalize(r["Model Pick"]) == normalize(r["Away Team"])
        odds_col = "Away" if is_away else "Home"
        return is_dog(r.get(odds_col, 0))
    model_dogs = model_plays[model_plays.apply(check_dog_pick, axis=1)].copy()

signals = pd.DataFrame()
if not model_plays.empty and sharp_col in df.columns:
    signals = model_plays[
        model_plays.apply(
            lambda r: (str(r[sharp_col]).strip() != "" and normalize(r["Model Pick"]) == normalize(r[sharp_col])),
            axis=1
        )
    ].copy()


# ============================================================
# LAYOUT RENDERING
# ============================================================

st.title("⚾ MLB Command Center")
st.caption("Synchronized sheet tracking engine.")

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
