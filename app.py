import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# ============================================================
# PRODUCTION PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MLB Quantitative Command Center",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Elite Dark/High-Contrast UI Styling Injection
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
        h1 { font-weight: 900 !important; color: #111111 !important; letter-spacing: -1px; }
        h3 { font-weight: 700 !important; color: #2C3E50 !important; }
        
        /* Metric Block Custom Styling */
        div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 800 !important; color: #1E8449 !important; }
        
        /* Modern Tab Navigation Layout */
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #F8F9F9;
            border: 1px solid #E5E7E9;
            border-radius: 6px 6px 0px 0px;
            padding: 12px 24px;
            color: #5D6D7E;
            font-weight: 700;
            transition: all 0.2s ease-in-out;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #1E8449 !important;
            border-top: 3px solid #1E8449 !important;
            border-bottom: 1px solid #FFFFFF !important;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
        }
        
        /* Dynamic Monitor Panel */
        .monitor-card {
            background-color: #F2F4F4;
            border-left: 5px solid #2980B9;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)


# ============================================================
# LIVE PARAMETER CONFIGURATION (SIDEBAR CONTROL KNOBS)
# ============================================================
st.sidebar.markdown("## ⚙️ Quantitative Control Knobs")
st.sidebar.markdown("Adjust systematic thresholds in real-time to filter market inefficiencies.")

EV_THRESHOLD = st.sidebar.slider("Minimum Expected Value (EV)", min_value=0.0, max_value=25.0, value=5.0, step=0.5)
DIFF_THRESHOLD = st.sidebar.slider("Minimum Probability Delta (Diff %)", min_value=0.0, max_value=20.0, value=5.0, step=0.5)

st.sidebar.write("---")
st.sidebar.markdown("### 📊 Market Exposure Rules")
st.sidebar.info(
    f"Current Settings requiring **EV > {EV_THRESHOLD}** AND **Diff ≥ {DIFF_THRESHOLD}%** to trigger an automated system execution side."
)


# ============================================================
# PIPELINE: DATA INGESTION & ROBUST PARSING
# ============================================================
SHEET_ID = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
SHEET_NAME = "APP_EXPORT"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}&skiprows=1"

@st.cache_data(ttl=15)
def load_and_sanitize_market_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = [str(c).strip() for c in raw_df.columns]
        return raw_df.fillna("")
    except Exception as e:
        st.error(f"⚠️ Critical Pipeline Sync Fault: {e}")
        return pd.DataFrame()

def clean_numerical_vector(val):
    try:
        return float(str(val).replace("%", "").replace("+", "").replace(",", "").strip())
    except ValueError:
        return 0.0

def evaluate_tactical_side(row, ev_limit, diff_limit):
    away_ev = clean_numerical_vector(row.get("EV Away", 0))
    home_ev = clean_numerical_vector(row.get("EV Home", 0))
    away_diff = clean_numerical_vector(row.get("Diff Away", 0))
    home_diff = clean_numerical_vector(row.get("Diff Home", 0))

    away_valid = away_ev > ev_limit and away_diff >= diff_limit
    home_valid = home_ev > ev_limit and home_diff >= diff_limit

    if away_valid and (away_ev >= home_ev or not home_valid):
        return pd.Series([row["Away Team"], "Away", away_ev, away_diff, row["Away Odds"]])
    if home_valid and (home_ev > away_ev or not away_valid):
        return pd.Series([row["Home Team"], "Home", home_ev, home_diff, row["Home Odds"]])
    
    return pd.Series(["PASS", "Pass", max(away_ev, home_ev), max(away_diff, home_diff), ""])


# ============================================================
# COMPILING WORKSPACE DATASETS
# ============================================================
base_df = load_and_sanitize_market_data()
if base_df.empty: st.stop()

# Confirm structural node presence
required_nodes = [
    "Away Team", "Home Team", "Away Odds", "Home Odds", "Sharp Away", "Sharp Home", "Sharp Dog",
    "Vegas Win Away", "Vegas Win Home", "My Win Away", "My Win Home", "Diff Away", "Diff Home", 
    "EV Away", "EV Home", "O/U", "Over", "% O/U", "Sharps Totals Away"
]
missing_nodes = [n for n in required_nodes if n not in base_df.columns]
if missing_nodes:
    st.error(f"❌ Aborting. Column signature mismatch. Missing nodes: {missing_nodes}")
    st.stop()

# STAGE 1 CLEANING OVERRIDE: Drop rows where EITHER name is missing or whitespace to correct grid offsets
base_df = base_df[
    (base_df["Away Team"].astype(str).str.strip() != "") & 
    (base_df["Home Team"].astype(str).str.strip() != "") &
    (~base_df["Away Team"].astype(str).str.contains("Unnamed"))
].copy().reset_index(drop=True)

# Run Vectorized Engine Mapping dynamically factoring in User's Sidebar Control Knobs
base_df[["Model Pick", "Pick Side", "Pick EV", "Pick Diff", "Pick Odds"]] = base_df.apply(
    lambda r: evaluate_tactical_side(r, EV_THRESHOLD, DIFF_THRESHOLD), axis=1
)

# Apply Tier Grades on the fly
def assign_tier_grade(row):
    ev = row["Pick EV"]
    diff = row["Pick Diff"]
    if ev >= 20 and diff >= 10: return "Strong Play"
    if ev >= 10 and diff >= 5: return "Playable"
    if ev > 5: return "Lean"
    return "Pass"

base_df["Grade"] = base_df.apply(assign_tier_grade, axis=1)


# ============================================================
# HIGH-PERFORMANCE GRID COMPILER ENGINE
# ============================================================
def compile_interactive_grid(target_df, mode="sides", grid_height=450):
    if mode == "totals":
        display_cols = [
            "Away Team", "Home Team", "O/U", "Over", "% O/U", "Sharps Totals Away"
        ]
    else:
        display_cols = [
            "Away Team", "Home Team", "Away Odds", "Home Odds", "Sharp Away",
            "Sharp Home", "Sharp Dog", "Vegas Win Away", "Vegas Win Home",
            "My Win Away", "My Win Home", "Diff Away", "Diff Home", "EV Away",
            "EV Home", "Model Pick", "Pick Side", "Pick Odds", "Pick EV",
            "Pick Diff", "Grade"
        ]
        
    valid_cols = [c for c in display_cols if c in target_df.columns]
    working_df = target_df[valid_cols].copy()

    gb = GridOptionsBuilder.from_dataframe(working_df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=115)
    gb.configure_grid_options(rowHeight=38, headerHeight=42, rowSelection="single")

    gb.configure_column("Away Team", pinned="left", width=130, cellStyle={"fontWeight": "800", "color": "#111111"})
    gb.configure_column("Home Team", pinned="left", width=130, cellStyle={"fontWeight": "800", "color": "#111111"})
    
    if mode == "totals":
        gb.configure_column("O/U", width=100, cellStyle={"fontWeight": "700", "textAlign": "center"})
        gb.configure_column("Over", width=110, cellStyle=JsCode("""
            function(p) {
                if (p.value === 'OVER') return {backgroundColor: '#D4EFDF', color: '#196F3D', fontWeight: 'bold', textAlign: 'center'};
                if (p.value === 'UNDER') return {backgroundColor: '#FADBD8', color: '#78281F', fontWeight: 'bold', textAlign: 'center'};
                return {textAlign: 'center'};
            }
        """))
        gb.configure_column("% O/U", cellStyle=JsCode("""
            function(p) {
                let v = parseFloat(String(p.value).replace('%','').trim());
                if(isNaN(v)) return {};
                if(v >= 60) return {backgroundColor: '#FCF3CF', color: '#7D6608', fontWeight: 'bold'};
                return {};
            }
        """))
        gb.configure_column("Sharps Totals Away", cellStyle=JsCode("""
            function(p) {
                let v = parseFloat(String(p.value).replace('%','').trim());
                if(isNaN(v)) return {};
                return v > 0 ? {backgroundColor: '#E8F8F5', color: '#117A65', fontWeight: '700'} : {backgroundColor: '#FBEEF8', color: '#884EA0', fontWeight: '700'};
            }
        """))
    else:
        gb.configure_column("Model Pick", pinned="right", width=130, cellStyle=JsCode("""
            function(p) { return p.value === 'PASS' ? {backgroundColor: '#EBEDEF', color: '#7F8C8D'} : {backgroundColor: '#27AE60', color: '#ffffff', fontWeight: '900', textAlign: 'center'}; }
        """))
        gb.configure_column("Grade", pinned="right", width=115, cellStyle=JsCode("""
            function(p) {
                if (p.value === 'Strong Play') return {backgroundColor: '#1E8449', color: '#ffffff', fontWeight: 'bold'};
                if (p.value === 'Playable') return {backgroundColor: '#2ECC71', color: '#111111'};
                if (p.value === 'Lean') return {backgroundColor: '#F1C40F', color: '#111111'};
                return {backgroundColor: '#EBEDEF', color: '#7F8C8D'};
            }
        """))

    ev_format_script = JsCode("""
        function(p) {
            let v = parseFloat(String(p.value).trim());
            if(isNaN(v)) return {color: '#111111'};
            if(v >= 15) return {backgroundColor: '#2196F3', color: '#ffffff', fontWeight: 'bold'};
            if(v > 0) return {backgroundColor: '#E3F2FD', color: '#0D47A1'};
            if(v < 0) return {backgroundColor: '#FFEBEE', color: '#C62828'};
            return {color: '#111111'};
        }
    """)
    
    odds_format_script = JsCode("""
        function(p) {
            let v = parseFloat(String(p.value).replace('+','').trim());
            if(isNaN(v)) return {color: '#111111'};
            return v > 0 ? {backgroundColor: '#E8F8F5', color: '#117A65', fontWeight: '700'} : {backgroundColor: '#FBEEF8', color: '#884EA0', fontWeight: '700'};
        }
    """)

    if mode != "totals":
        for ev_col in ["EV Away", "EV Home", "Pick EV"]:
            if ev_col in working_df.columns: gb.configure_column(ev_col, cellStyle=ev_format_script)
        for odds_col in ["Away Odds", "Home Odds", "Pick Odds"]:
            if odds_col in working_df.columns: gb.configure_column(odds_col, cellStyle=odds_format_script)

    g_options = gb.build()
    
    response = AgGrid(
        working_df,
        gridOptions=g_options,
        height=grid_height,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        theme="alpine",
        enable_enterprise_modules=False,
        update_mode="MODEL_CHANGED"
    )
    return response


# ============================================================
# MASTER SUITE CORE VIEWPORTS
# ============================================================
st.title("⚾ MLB Quantitative Command Center")
st.caption("High-velocity computational matrix driving predictive delta analysis.")

# System Diagnostics Row
total_active_slate = len(base_df)
active_execution_plays = base_df[base_df["Model Pick"] != "PASS"]
sharp_money_nodes = base_df[base_df["Sharp Dog"].astype(str).str.strip() != ""]
confluence_nodes = base_df[base_df.apply(lambda r: (str(r["Sharp Dog"]).strip() != "" and str(r["Model Pick"]).strip().upper() == str(r["Sharp Dog"]).strip().upper()), axis=1)]

idx_c1, idx_c2, idx_c3, idx_c4 = st.columns(4)
idx_c1.metric("Slate Volume", total_active_slate)
idx_c2.metric("Execution Triggers", len(active_execution_plays))
idx_c3.metric("Sharp Monitored Assets", len(sharp_money_nodes))
idx_c4.metric("Systemic Confluences", len(confluence_nodes))

st.write("---")

# ============================================================
# REAL-TIME CONSOLE VARIABLE MONITOR PANEL
# ============================================================
st.markdown("### 🖥️ Live Node Telemetry")
st.markdown("<small>Select any row inside the data grids below to instantly lock and track that specific match variable array.</small>", unsafe_allow_html=True)

monitor_anchor = st.empty()

tab_all, tab_ou, tab_premium, tab_sharps, tab_confluence, tab_guide = st.tabs([
    "All Games Matrix", "Over/Under Matrix", "Top System Plays", "Sharp Money Tracker", "System Confluence Signals", "📖 System Logic Guide"
])

# STAGE 2 ALIGNMENT OVERRIDE: Bind the base state explicitly to the actual 1st item of our newly structured dataframe
selected_row_data = base_df.iloc[0].to_dict() if not base_df.empty else None

with tab_all:
    st.markdown("### Master Active Board")
    grid_response = compile_interactive_grid(base_df, mode="sides", grid_height=500)
    if grid_response.selected_rows is not None and not grid_response.selected_rows.empty:
        selected_row_data = grid_response.selected_rows.iloc[0].to_dict()

with tab_ou:
    st.markdown("### Model & Sharp Over/Under Projections")
    ou_grid_response = compile_interactive_grid(base_df, mode="totals", grid_height=500)
    if ou_grid_response.selected_rows is not None and not ou_grid_response.selected_rows.empty:
        selected_row_data = ou_grid_response.selected_rows.iloc[0].to_dict()

with tab_premium:
    st.markdown("### Premium Algorithmic Formations")
    if not active_execution_plays.empty:
        top_premium = active_execution_plays.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False]).head(5)
        premium_grid_response = compile_interactive_grid(top_premium, mode="sides", grid_height=300)
        if premium_grid_response.selected_rows is not None and not premium_grid_response.selected_rows.empty:
            selected_row_data = premium_grid_response.selected_rows.iloc[0].to_dict()
    else:
        st.info("No formations currently clear the Sidebar execution parameters.")

with tab_sharps:
    st.markdown("### Tracked Sharp Syndicate Placements")
    if not sharp_money_nodes.empty:
        sharp_sorted = sharp_money_nodes.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])
        sharp_grid_response = compile_interactive_grid(sharp_sorted, mode="sides", grid_height=350)
        if sharp_grid_response.selected_rows is not None and not sharp_grid_response.selected_rows.empty:
            selected_row_data = sharp_grid_response.selected_rows.iloc[0].to_dict()
    else:
        st.info("No active sharp delta found on the current slate export.")

with tab_confluence:
    st.markdown("### Institutional Model Convergence Points")
    if not confluence_nodes.empty:
        confluence_sorted = confluence_nodes.sort_values(by=["Pick EV", "Pick Diff"], ascending=[False, False])
        conf_grid_response = compile_interactive_grid(confluence_sorted, mode="sides", grid_height=350)
        if conf_grid_response.selected_rows is not None and not conf_grid_response.selected_rows.empty:
            selected_row_data = conf_grid_response.selected_rows.iloc[0].to_dict()
    else:
        st.info("No structural convergence points detected between model parameters and sharp actions.")

with tab_guide:
    st.markdown("### Matrix Structural Protocols")
    gl, gr = st.columns(2)
    with gl:
        st.markdown("""
        #### 📈 System Parameters
        * **Target Strategy:** Ingests live sportsbook baseline structures, parses implied payout probabilities, and runs real-time difference comparison to your internal model calculations.
        * **Formula Node Array:** Target selection triggers when `EV > Threshold` AND `Diff >= Threshold` simultaneously.
        """)
    with gr:
        st.markdown("""
        #### 🎨 Micro-Color Classifications
        * **Blue Grid Highlights:** Captures outsized mathematical expected value arrays ($\ge$ 15 EV margin).
        * **Soft Green / Purple Odds Blocks:** Isolates underdogs vs favorites dynamically via line structure orientation.
        """)

# Render variables dynamically inside telemetry module
if selected_row_data is not None:
    t_away = selected_row_data.get("Away Team", "N/A")
    t_home = selected_row_data.get("Home Team", "N/A")
    v_win_away = selected_row_data.get("Vegas Win Away", "0%")
    v_win_home = selected_row_data.get("Vegas Win Home", "0%")
    m_win_away = selected_row_data.get("My Win Away", "0%")
    m_win_home = selected_row_data.get("My Win Home", "0%")
    
    # Safely format model vector projections for display output
    p_ev = selected_row_data.get("Pick EV", 0.0)
    p_diff = selected_row_data.get("Pick Diff", 0.0)
    p_pick = selected_row_data.get("Model Pick", "PASS")
    p_grade = selected_row_data.get("Grade", "Pass")
    s_dog = selected_row_data.get("Sharp Dog", "")
    
    ou_line = selected_row_data.get("O/U", "N/A")
    ou_side = selected_row_data.get("Over", "PASS")
    ou_pct = selected_row_data.get("% O/U", "0%")
    sharp_tot_a = selected_row_data.get("Sharps Totals Away", "0%")

    with monitor_anchor.container():
        st.markdown(f"""
        <div class="monitor-card">
            <h4>⚡ TRACKING METRIC ARRAY: {t_away} vs {t_home}</h4>
            <table style="width:100%; border:none; font-family:monospace; font-size:14px; color:#2C3E50; border-collapse: separate; border-spacing: 0 8px;">
                <tr>
                    <td style="width: 33%;"><b>System Verdict:</b> <span style="color:#1E8449; font-weight:800;">{p_pick} ({p_grade})</span></td>
                    <td style="width: 33%;"><b>Calculated EV Edge:</b> {p_ev}</td>
                    <td style="width: 33%;"><b>Win Split Delta:</b> +{p_diff}%</td>
                </tr>
                <tr>
                    <td><b>Vegas Implied Projection:</b> A: {v_win_away} | H: {v_win_home}</td>
                    <td><b>Your Model Implied:</b> A: {m_win_away} | H: {m_win_home}</td>
                    <td><b>Sharp Syndicate Side:</b> <span style="color:#2980B9; font-weight:700;">{s_dog if s_dog else 'None Detected'}</span></td>
                </tr>
                <tr style="border-top: 1px solid #BDC3C7;">
                    <td><b>O/U Line Target:</b> <span style="font-weight:700; color:#8E44AD;">{ou_line} ({ou_side})</span></td>
                    <td><b>Model Total Edge:</b> {ou_pct}</td>
                    <td><b>Sharp Totals Delta (Away):</b> {sharp_tot_a}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
