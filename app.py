import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MLB Command Center",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Force a clean dark theme container for the Streamlit background
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1 { font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -1px; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #1e1e24;
            border-radius: 6px 6px 0px 0px;
            padding: 10px 20px;
            color: #afb1b6;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2d3139 !important;
            color: #00ff66 !important;
            border-bottom: 2px solid #00ff66 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEET SETTINGS
# ============================================================

SHEET_ID = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
SHEET_NAME = "APP_EXPORT"

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
        return float(str(v).replace("%", "").replace("+", "").replace(",", "").strip())
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

    if ev >= 20 and diff >= 10: return "Strong Play"
    if ev >= 10 and diff >= 5: return "Playable"
    if ev > 5: return "Lean"
    return "Pass"


def prepare_display(df):
    cols = [
        "Away Team", "Home Team", "Away Odds", "Home Odds", "Sharp Away",
        "Sharp Home", "Sharp Dog", "Vegas Win Away", "Vegas Win Home",
        "My Win Away", "My Win Home", "Diff Away", "Diff Home", "EV Away",
        "EV Home", "Model Pick", "Pick Side", "Pick Odds", "Pick EV",
        "Pick Diff", "Grade",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()


# ============================================================
# MODERNIZED DARK AGGRID BOARD
# ============================================================

def show_grid(df, height=825):
    display_df = prepare_display(df)

    gb = GridOptionsBuilder.from_dataframe(display_df)

    # Global UI Overhaul
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=True,
        minWidth=120,
        wrapText=False,
        autoHeight=False,
    )

    # Layout Spacing Controls
    gb.configure_grid_options(
        rowHeight=42,
        headerHeight=48,
        rowSelection="single"
    )

    # Pinned Navigation Pillars
    if "Away Team" in display_df.columns:
        gb.configure_column("Away Team", pinned="left", width=140, cellStyle={"fontWeight": "700", "color": "#FFFFFF"})

    if "Home Team" in display_df.columns:
        gb.configure_column("Home Team", pinned="left", width=140, cellStyle={"fontWeight": "700", "color": "#FFFFFF"})

    # Pro-Grade Dark Color Mappings (Glow effects rather than flat solids)
    ev_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('%','').trim());
        if (isNaN(val)) return {};
        if (val >= 20) return {backgroundColor: 'rgba(0, 166, 81, 0.25)', color: '#00ff66', fontWeight: 'bold'};
        if (val >= 10) return {backgroundColor: 'rgba(125, 206, 160, 0.15)', color: '#7DCEA0'};
        if (val > 0) return {backgroundColor: 'rgba(213, 245, 227, 0.05)', color: '#D5F5E3'};
        if (val < 0) return {backgroundColor: 'rgba(245, 183, 177, 0.08)', color: '#F5B7B1'};
        return {};
    }
    """)

    diff_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('%','').trim());
        if (isNaN(val)) return {};
        if (val >= 10) return {backgroundColor: 'rgba(88, 214, 141, 0.25)', color: '#58D68D', fontWeight: 'bold'};
        if (val >= 5) return {backgroundColor: 'rgba(249, 231, 159, 0.15)', color: '#F9E79F', fontWeight: 'bold'};
        if (val <= -10) return {backgroundColor: 'rgba(241, 148, 138, 0.12)', color: '#F1948A'};
        return {};
    }
    """)

    pick_style = JsCode("""
    function(params) {
        if (params.value === 'PASS') return {backgroundColor: 'rgba(255,255,255,0.04)', color: '#71747c'};
        if (params.value) return {backgroundColor: '#1E8449', color: '#ffffff', fontWeight: '900', textAlign: 'center'};
        return {};
    }
    """)

    sharp_style = JsCode("""
    function(params) {
        if (params.value && String(params.value).trim() !== '') {
            return {backgroundColor: 'rgba(52, 152, 219, 0.2)', color: '#5dade2', fontWeight: 'bold', border: '1px solid #3498db'};
        }
        return {};
    }
    """)

    grade_style = JsCode("""
    function(params) {
        if (params.value === 'Strong Play') return {color: '#00ff66', fontWeight: '900', backgroundColor: 'rgba(0, 166, 81, 0.1)'};
        if (params.value === 'Playable') return {color: '#7DCEA0', fontWeight: 'bold'};
        if (params.value === 'Lean') return {color: '#F9E79F'};
        if (params.value === 'Pass') return {color: '#71747c'};
        return {};
    }
    """)

    odds_style = JsCode("""
    function(params) {
        let val = parseFloat(String(params.value).replace('+','').trim());
        if (isNaN(val)) return {};
        if (val > 0) return {color: '#3498db', fontWeight: 'bold', backgroundColor: 'rgba(52, 152, 219, 0.05)'};
        if (val < 0) return {color: '#e74c3c', fontWeight: 'bold', backgroundColor: 'rgba(231, 76, 60, 0.05)'};
        return {};
    }
    """)

    signal_row_style = JsCode("""
    function(params) {
        let pick = params.data["Model Pick"];
        let sharp = params.data["Sharp Dog"];
        if (pick && sharp && pick !== "PASS" && String(pick).trim().toUpperCase() === String(sharp).trim().toUpperCase()) {
            return {backgroundColor: '#1c2833', borderLeft: '4px solid #3498db'};
        }
        return {};
    }
    """)

    # Apply style assignments
    for col in ["EV Away", "EV Home", "Pick EV"]:
        if col in display_df.columns: gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=ev_style)

    for col in ["Diff Away", "Diff Home", "Pick Diff"]:
        if col in display_df.columns: gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=diff_style)

    for col in ["Away Odds", "Home Odds", "Pick Odds"]:
        if col in display_df.columns: gb.configure_column(col, width=115, type=["numericColumn"], cellStyle=odds_style)

    if "Sharp Dog" in display_df.columns: gb.configure_column("Sharp Dog", width=125, cellStyle=sharp_style)
    if "Model Pick" in display_df.columns: gb.configure_column("Model Pick", pinned="right", width=140, cellStyle=pick_style)
    if "Grade" in display_df.columns: gb.configure_column("Grade", pinned="right", width=120, cellStyle=grade_style)

    for col in ["Sharp Away", "Sharp Home", "Vegas Win Away", "Vegas Win Home", "My Win Away", "My Win Home"]:
        if col in display_df.columns: gb.configure_column(col, width=125, cellStyle={"color": "#cccccc"})

    grid_options = gb.build()
    grid_options["getRowStyle"] = signal_row_style

    AgGrid(
        display_df,
        gridOptions=grid_options,
        height=height,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        theme="alpine-dark",  # Clean, modern charcoal/black framework
        enable_enterprise_modules=False,
    )


# ============================================================
# LOAD + VALIDATE
# ============================================================

df = load_data()
if df.empty: st.stop()

required_cols = [
    "Away Team", "Home Team", "Away Odds", "Home Odds", "Sharp Away",
    "Sharp Home", "Sharp Dog", "Vegas Win Away", "Vegas Win Home",
    "My Win Away", "My Win Home", "Diff Away", "Diff Home", "EV Away", "EV Home"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing columns in APP_EXPORT: {missing}")
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

df["Grade"] = df.apply(lambda r: grade_play(r["Pick EV"], r["Pick Diff"]), axis=1)


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

# Metric Panel Styles
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Games On Board", len(df))
c2.metric("Active Model Plays", len(model_plays))
c3.metric("Tracked Sharp Dogs", len(sharp_dogs))
c4.metric("Model Underdogs", len(model_dogs))
c5.metric("System Confluence Signals", len(signals))

# Master Tabs Layout
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📖 How to Read", "All Games", "Top 5 Plays", "Sharp Dogs", "Model Dogs", "Signal Plays"
])

with tab0:
    st.subheader("System Rules & Interpretation Playbook")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("""
        ### 🎯 Core Execution Thresholds
        The model checks specific edge benchmarks for both `Away` and `Home` columns to calculate valid selections. A team is strictly targeted **only** if it ticks both parameters simultaneously:
        * **Expected Value (EV):** Must be strictly greater than **5.0** (`EV > 5`).
        * **Win Percentage Differential (Diff):** Must be equal to or greater than **5.0** (`Diff >= 5`).
        
        ### 📊 Play Tier Grading
        When a play is identified, its strength is categorized dynamically according to the final **Pick EV** and **Pick Diff** values:
        * 🟢 **Strong Play:** EV $\ge$ 20 AND Diff $\ge$ 10.
        * 🟡 **Playable:** EV $\ge$ 10 AND Diff $\ge$ 5.
        * 🔵 **Lean:** EV $>$ 5 AND Diff $\ge$ 5.
        * ⚪ **Pass:** Fails to meet baseline limits.
        """)
        
    with col_right:
        st.markdown("""
        ### 🔍 Reading the Market Segments
        #### 📉 Favorites vs. 🐶 Underdogs
        The application isolates the line pricing based on standard American odds notations:
        * **Favorites (Minus Money):** Displayed with negative red-tinted values. High market probability hooks.
        * **Underdogs (Plus Money / Dogs):** Isolated via the **Model Dogs** tracking layer whenever `Odds > 0`. High-leverage inefficiency models.
        
        #### 📈 Sharp Action & Convergence Signals
        * **Sharp Tracking:** Denotes where professional trading syndicates are exposing risk capital.
        * **Convergence Signals:** Found in the **Signal Plays** panel. Triggers when the **Model Pick** cleanly matches the designated **Sharp Dog**. These custom rows highlight inside the grid to track systemic alignment.
        """)

with tab1:
    st.subheader("All Boarded Formations")
    show_grid(df, height=850)

with tab2:
    st.subheader("Top 5 Premium System Plays")
    if top_plays.empty: st.info("No active model plays found.")
    else: show_grid(top_plays, height=500)

with tab3:
    st.subheader("Sharp Syndicate Underdog Targets")
    if sharp_dogs.empty: st.info("No sharp dogs listed.")
    else: show_grid(sharp_dogs, height=850)

with tab4:
    st.subheader("Model Edge Underdog Formations")
    if model_dogs.empty: st.info("No model underdog plays found.")
    else: show_grid(model_dogs, height=850)

with tab5:
    st.subheader("System Confluence (Model & Sharp Alignment)")
    if signals.empty: st.info("No sharp/model alignment plays found.")
    else: show_grid(signals, height=850)
