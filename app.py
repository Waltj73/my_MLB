import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# GID for the "Model" tab is usually found in the URL when you click it
GID = '0' # GID 0 is typically the first tab ("Model")
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Load the CSV, skip the first row (the "Teams", "Vegas Odds" headers)
        # and use the second row (Away Team, Home Team) as the header.
        df = pd.read_csv(URL, skiprows=1)
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI & MAPPING ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        def to_f(v):
            return pd.to_numeric(str(v).replace('%','').replace(',','').strip(), errors='coerce')

        # COLUMN MAPPING BASED ON image_1f6ff9.png
        # Column indexing starts at 0 (A=0, B=1, E=4, F=5, S=18, T=19, W=22, X=23)
        col_away = 0
        col_home = 1
        col_v_away = 4
        col_v_home = 5
        col_my_away = 18
        col_my_home = 19
        col_ev_away = 22
        col_ev_home = 23

        # Matchup Selector
        matchups = (df.iloc[:, col_away].astype(str) + " @ " + df.iloc[:, col_home].astype(str)).tolist()
        # Filter out empty rows
        matchups = [m for m in matchups if "nan" not in m.lower()]
        
        selected = st.selectbox("🎯 Select Matchup", matchups)
        g = df[(df.iloc[:, col_away].astype(str) + " @ " + df.iloc[:, col_home].astype(str)) == selected].iloc[0]

        # Scouting Report
        st.header(f"📈 Scouting Report: {g.iloc[col_away]} @ {g.iloc[col_home]}")
        
        m1, m2, m3 = st.columns(3)
        
        # Pulling your pre-calculated Win % and EV directly from the sheet
        m1.metric("Model Win % (Away)", f"{g.iloc[col_my_away]}")
        m2.metric("EV (Away)", f"{g.iloc[col_ev_away]}")
        m3.metric("Vegas Odds (Away)", f"{g.iloc[col_v_away]}")

        st.divider()
        st.write(f"📊 **Sheet Data**: Viewing current projections for {g.iloc[col_home]} (Home).")
        
    except Exception as e:
        st.warning(f"Map Error: {e}")
        st.write("Ensure the 'Model' tab starts with headers in Row 1 & 2.")
else:
    st.info("🔄 Connecting to 'Model' tab...")
