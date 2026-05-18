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

# Elite UI Styling Injection
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
        
        /* Telemetry Cheat Sheet Note Block */
        .telemetry-note {
            margin-top: 12px;
            padding-top: 8px;
            border-top: 1px dashed #BDC3C7;
            font-size: 12px;
            color: #566573;
        }
    </style>
""", unsafe_allow_html=True)


# ============================================================
# PIPELINE: DATA INGESTION & AUTOMATED CLEANING
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


# ============================================================
# COMPILING WORKSPACE DATASETS
# ============================================================
base_df = load_and_sanitize_market_data()
if base_df.empty: st.stop()

# Safely drop empty structural placeholder lines from the sheet
base_df = base_df[
    (base_df["Home Team"].astype(str).str.strip() != "") & 
    (~base_df["Home Team"].astype(str).str.contains("Unnamed"))
].copy().reset_index(drop=True)

# Generate a permanent immutable key identifier for cross-tab row locking
base_df["_match_id"] = base_df["Away Team"].astype(str) + "_" + base_df["Home Team"].astype(str)

# Helper function to convert text strings safely into numbers for sorting/logic
def clean_numerical_vector(val):
    try:
        return float(str(val).replace("%", "").replace("+", "").replace(",", "").strip())
    except ValueError:
        return 0.0

# AUTOMATED COLUMN SIGNATURE DETECTOR
PICK_COL = "Pick" if "Pick" in base_df.columns else "Model Pick" if "Model Pick" in base_df.columns else None

if not PICK_COL:
    st.error("❌ Column Mapping Fault: Could not detect a 'Pick' or 'Model Pick' column header in your Google Sheet.")
    st.stop()


# ============================================================
# BULLETPROOF INTERACTIVE GRID COMPILER ENGINE
# ============================================================
def compile_interactive_grid(target_df, mode="sides", grid_key="grid"):
    gb = GridOptionsBuilder.from_dataframe(target_df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, minWidth=115)
    gb.configure_grid_options(rowHeight=38, headerHeight=42, rowSelection="single", preSelectAllRows=False)

    # Hide backend utility tracking metrics from screen views
    if "_match_id" in target_df.columns: gb.configure_column("_match_id", hide=True)
    if "_sort_ev" in target_df.columns: gb.configure_column("_sort_ev", hide=True)

    if "Away Team" in target_df.columns:
        gb.configure_column("Away Team", pinned="left", width=130, cellStyle={"fontWeight": "800", "color": "#111111"})
    if "Home Team" in target_df.columns:
        gb.configure_column("Home Team", pinned="left", width=130, cellStyle={"fontWeight": "800", "color": "#111111"})
    
    if mode == "totals":
        if "O/U" in target_df.columns:
            gb.configure_column("O/U", width=100, cellStyle={"fontWeight": "700", "textAlign": "center"})
        if "Over" in target_df.columns:
            gb.configure_column("Over", width=110, cellStyle=JsCode("""
                function(p) {
                    if (p.value === 'OVER') return {backgroundColor: '#D4EFDF', color: '#196F3D', fontWeight: 'bold', textAlign: 'center'};
                    if (p.value === 'UNDER') return {backgroundColor: '#FADBD8', color: '#78281F', fontWeight: 'bold', textAlign: 'center'};
                    return {textAlign: 'center'};
                }
            """))
    else:
        if PICK_COL in target_df.columns:
            gb.configure_column(PICK_COL, pinned="right", width=140, cellStyle=JsCode("""
                function(p) { 
                    if (!p.value || String(p.value).trim() === '' || String(p.value).toUpperCase() === 'PASS') {
                        return {backgroundColor: '#EBEDEF', color: '#7F8C8D', textAlign: 'center'};
                    }
                    return {backgroundColor: '#27AE60', color: '#ffffff', fontWeight: '900', textAlign: 'center'}; 
                }
            """))

    ev_format_script = JsCode("""
        function(p) {
            let v = parseFloat(String(p.value).replace('%','').trim());
            if(isNaN(v)) return {color: '#111111'};
            if(v >= 15) return {backgroundColor: '#2196F3', color: '#ffffff', fontWeight: 'bold'};
            if(v > 0) return {backgroundColor: '#E3F2FD', color: '#0D47A1'};
            if(v < 0) return {backgroundColor: '#FFEBEE', color: '#C62828'};
            return {color: '#111111'};
        }
    """)

    if mode != "totals":
        for ev_col in ["EV Away", "EV Home", "Pick EV", "EV"]:
            if ev_col in target_df.columns: 
                gb.configure_column(ev_col, cellStyle=ev_format_script)

    g_options = gb.build()
    
    return AgGrid(
        target_df,
        gridOptions=g_options,
        height=480,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        theme="alpine",
        key=grid_key,
        update_mode="MODEL_CHANGED"
    )


# ============================================================
# BULLETPROOF DATA ROUTING RUNTIME STATE LISTENER
# ============================================================
def extract_selected_match_id(response):
    if response is None or not hasattr(response, "selected_rows"):
        return None
    s_rows = response.selected_rows
    if s_rows is None:
        return None
        
    # Handle dictionary payload structure (AgGrid standard variation)
    if isinstance(s_rows, dict):
        if "id" in s_rows or "_match_id" in s_rows:
            return s_rows.get("_match_id")
        # Handle structural nested layouts inside dictionary indices
        for key in s_rows.keys():
            if isinstance(s_rows[key], list) and len(s_rows[key]) > 0:
                inner = s_rows[key][0]
                if isinstance(inner, dict): return inner.get("_match_id")
                
    # Handle pure list structural return values
    if isinstance(s_rows, list) and len(s_rows) > 0:
        target_item = s_rows[0]
        if isinstance(target_item, dict):
            return target_item.get("_match_id")
        if hasattr(target_item, "get"):
            return target_item.get("_match_id")
            
    # Handle direct Pandas DataFrame serialization outputs
    if isinstance(s_rows, pd.DataFrame):
        if not s_rows.empty:
            return s_rows.iloc[0].get("_match_id")
            
    return None


# ============================================================
# MASTER SUITE CORE VIEWPORTS
# ============================================================
st.title("⚾ MLB Quantitative Command Center")
st.caption("High-velocity computational matrix driving predictive delta analysis.")

# System Diagnostics Datasets
active_execution_triggers = base_df[(base_df[PICK_COL].astype(str).str.strip() != "") & (base_df[PICK_COL].astype(str).str.upper() != "PASS")]
sharp_money_nodes = base_df[base_df["Sharp Dog"].astype(str).str.strip() != ""] if "Sharp Dog" in base_df.columns else pd.DataFrame()
confluence_nodes = base_df[base_df.apply(lambda r: (str(r.get("Sharp Dog", "")).strip() != "" and str(r[PICK_COL]).strip().upper() == str(r.get("Sharp Dog", "")).strip().upper()), axis=1)] if "Sharp Dog" in base_df.columns else pd.DataFrame()

idx_c1, idx_c2, idx_c3, idx_c4 = st.columns(4)
idx_c1.metric("Slate Volume", len(base_df))
idx_c2.metric("Execution Triggers", len(active_execution_triggers))
idx_c3.metric("Sharp Monitored Assets", len(sharp_money_nodes))
idx_c4.metric("Systemic Confluences", len(confluence_nodes))

st.write("---")

st.markdown("### 🖥️ Live Node Telemetry")
st.markdown("<small>Select any row inside the data grids below to instantly lock and track that specific match variable array.</small>", unsafe_allow_html=True)

# 1. RESERVE THE MONITORED BOX GRAPHICAL AREA FIRST
monitor_anchor = st.empty()

# 2. RENDER INTERACTIVE TAB CORES
tab_all, tab_ou, tab_premium, tab_sharps, tab_confluence = st.tabs([
    "All Games Matrix", "Over/Under Matrix", "Top System Plays", "Sharp Money Tracker", "System Confluence Signals"
])

selected_match_id = None

with tab_all:
    grid_response = compile_interactive_grid(base_df, mode="sides", grid_key="all_games_matrix_grid")
    mid = extract_selected_match_id(grid_response)
    if mid: selected_match_id = mid

with tab_ou:
    ou_cols = [c for c in ["Away Team", "Home Team", "O/U", "Over", "% O/U", "Sharps Totals Away", "_match_id"] if c in base_df.columns]
    ou_df = base_df[ou_cols].copy() if ou_cols else base_df
    ou_grid_response = compile_interactive_grid(ou_df, mode="totals", grid_key="ou_matrix_grid")
    mid = extract_selected_match_id(ou_grid_response)
    if mid: selected_match_id = mid

with tab_premium:
    if not active_execution_triggers.empty:
        top_premium = active_execution_triggers.copy()
        
        def resolve_directional_ev(row):
            pick_string = str(row[PICK_COL]).strip().upper()
            away_string = str(row["Away Team"]).strip().upper()
            if pick_string == away_string:
                return clean_numerical_vector(row.get("EV Away", 0))
            else:
                return clean_numerical_vector(row.get("EV Home", 0))
                
        top_premium["_sort_ev"] = top_premium.apply(resolve_directional_ev, axis=1)
        top_premium = top_premium.sort_values(by="_sort_ev", ascending=False)
        
        premium_response = compile_interactive_grid(top_premium, mode="sides", grid_key="premium_grid")
        mid = extract_selected_match_id(premium_response)
        if mid: selected_match_id = mid
    else:
        st.info("No active execution plays found directly on the sheet.")

with tab_sharps:
    if not sharp_money_nodes.empty:
        sharp_response = compile_interactive_grid(sharp_money_nodes, mode="sides", grid_key="sharps_grid")
        mid = extract_selected_match_id(sharp_response)
        if mid: selected_match_id = mid
    else:
        st.info("No active sharp delta found on the current slate export.")

with tab_confluence:
    if not confluence_nodes.empty:
        conf_response = compile_interactive_grid(confluence_nodes, mode="sides", grid_key="confluence_grid")
        mid = extract_selected_match_id(conf_response)
        if mid: selected_match_id = mid
    else:
        st.info("No structural convergence points detected.")

# Core Cross-Tab Inversion Controller
if selected_match_id:
    matched_rows = base_df[base_df["_match_id"] == selected_match_id]
    runtime_selection = matched_rows.iloc[0].to_dict() if not matched_rows.empty else base_df.iloc[0].to_dict()
else:
    runtime_selection = base_df.iloc[0].to_dict() if not base_df.empty else None

# 3. BACKFILL RESERVED TELEMETRY BOX
if runtime_selection:
    t_away = runtime_selection.get("Away Team", "N/A")
    t_home = runtime_selection.get("Home Team", "N/A")
    v_win_away = runtime_selection.get("Vegas Win Away", "0%")
    v_win_home = runtime_selection.get("Vegas Win Home", "0%")
    m_win_away = runtime_selection.get("My Win Away", "0%")
    m_win_home = runtime_selection.get("My Win Home", "0%")
    
    p_ev_away = runtime_selection.get("EV Away", "0.0")
    p_ev_home = runtime_selection.get("EV Home", "0.0")
    p_diff_away = runtime_selection.get("Diff Away", "0.0")
    p_diff_home = runtime_selection.get("Diff Home", "0.0")
    
    p_pick = str(runtime_selection.get(PICK_COL, "")).strip()
    p_display_verdict = p_pick if p_pick != "" else "PASS"
    
    if p_display_verdict.upper() == str(t_away).upper():
        active_ev = f"<span style='color:#1E8449; font-weight:bold;'>{p_ev_away} (Away)</span>"
        active_diff = f"{p_diff_away} (Away)"
    elif p_display_verdict.upper() == str(t_home).upper():
        active_ev = f"<span style='color:#1E8449; font-weight:bold;'>{p_ev_home} (Home)</span>"
        active_diff = f"{p_diff_home} (Home)"
    else:
        active_ev = f"A: {p_ev_away} | H: {p_ev_home}"
        active_diff = f"A: {p_diff_away} | H: {p_diff_home}"
    
    s_dog = runtime_selection.get("Sharp Dog", "")
    ou_line = runtime_selection.get("O/U", "N/A")
    ou_side = runtime_selection.get("Over", "PASS")
    ou_pct = runtime_selection.get("% O/U", "0%")
    sharp_tot_a = runtime_selection.get("Sharps Totals Away", "0%")

    monitor_anchor.markdown(f"""
    <div class="monitor-card">
        <h4>⚡ TRACKING METRIC ARRAY: {t_away} vs {t_home}</h4>
        <table style="width:100%; border:none; font-family:monospace; font-size:14px; color:#2C3E50; border-collapse: separate; border-spacing: 0 8px;">
            <tr>
                <td style="width: 33%;"><b>System Verdict:</b> <span style="color:{'#27AE60' if p_display_verdict != 'PASS' else '#7F8C8D'}; font-weight:800;">{p_display_verdict}</span></td>
                <td style="width: 33%;"><b>Calculated EV Edge:</b> {active_ev}</td>
                <td style="width: 33%;"><b>Win Split Delta:</b> {active_diff}</td>
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
        <div class="telemetry-note">
            ℹ️ <b>i O/U Telemetry Interpretation Legend:</b><br>
            • <b>Positive %</b> in <i>Sharp Totals Delta (Away)</i>: Represents <b>UNDER</b> pressure. The sharps are hammering the under or suppressing the scoring volume.<br>
            • <b>Negative %</b> in <i>Sharp Totals Delta (Away)</i>: Represents <b>OVER</b> pressure. The sharps are backing the over, meaning they are letting the scoring environment expand.
        </div>
    </div>
    """, unsafe_allow_html=True)
