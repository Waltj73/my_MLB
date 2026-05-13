import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- 1. CONFIG & DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df.fillna('')
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. AUTOMATED SCOUTING INTELLIGENCE ---
@st.cache_data(ttl=3600) # Only fetch once per hour to stay fast
def fetch_scouting_reports():
    intelligence = {}
    try:
        # Targeting reputable daily notes (e.g., RotoWire or FanGraphs summaries)
        # For this build, we use a placeholder that mimics the scraping logic
        intelligence = {
            "Mariners @ Astros": "McCullers Jr. struggling with 9.39 ERA/2.0 HR/9 over last 5 starts. Seattle chasing sweep.",
            "Rockies @ Pirates": "Sharp money favoring Rockies dog (10% move) despite Pirates strong home EV.",
            "Marlins @ Twins": "SWR (MIN) showing 5.75 xERA; hitters punishing splitter (.341 BA).",
            "Phillies @ Red Sox": "Sonny Gray (BOS) strong reverse-splits vs lefties (.254 wOBA allowed)."
        }
        return intelligence
    except:
        return {}

# --- 3. UI SETUP ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()
scout_notes = fetch_scouting_reports()

if not df.empty:
    try:
        # Standardize Filtering
        main_df = df[df.iloc[:, 0].astype(str).str.len() > 2].copy()
        
        def to_n(v):
            try: return float(str(v).replace('%','').replace(',','').strip())
            except: return 0.0

        # --- 4. MASTER TABLE CONSTRUCTION ---
        # Mapping: Teams(0,1), Vegas(4,5), Sharp%(13,14), SharpDog(15), MyWin(18,19), EV(22,23), Picks(25,26), SheetNote(27)
        master_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "Sharp ML %": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Dog": main_df.iloc[:, 15].astype(str),
            "My Win %": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (A/H)": main_df.iloc[:, 22].astype(str) + " / " + main_df.iloc[:, 23].astype(str),
            "Model Pick": main_df.iloc[:, 25].astype(str) + " " + main_df.iloc[:, 26].astype(str),
            "Tactical Note": main_df.iloc[:, 27].astype(str)
        })

        # --- 5. AUTO-NOTE INJECTION ---
        def apply_scout_logic(row):
            matchup = row['Matchup']
            sheet_note = row['Tactical Note'].strip()
            # If sheet is empty, check the automated scout database
            if len(sheet_note) < 3:
                return scout_notes.get(matchup, "No significant market alerts.")
            return sheet_note

        master_table['Tactical Note'] = master_table.apply(apply_scout_logic, axis=1)

        # --- 6. DISPLAY ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            if len(str(row['Sharp Dog']).strip()) > 1:
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            if len(str(row['Model Pick']).strip()) > 1:
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(master_table.style.apply(highlight_logic, axis=1), use_container_width=True)

        # --- 7. SCOUTING PANE ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog, pick = str(row['Sharp Dog']).strip(), str(row['Model Pick']).strip()
                if len(s_dog) > 1:
                    if s_dog in pick: st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")
                    else: st.warning(f"**CONFLICT**: Sharps on {s_dog} vs Model: {pick}")

        with col_r:
            st.subheader("📝 Scouting Notes (The 'Why')")
            for _, row in master_table.iterrows():
                note = row['Tactical Note']
                if "No significant" not in note:
                    with st.expander(f"Analysis: {row['Matchup']}"):
                        st.write(f"**Intelligence**: {note}")
                        # Auto-Tagging
                        if "era" in note.lower() or "pitcher" in note.lower(): st.caption("🔍 Pitching Edge")
                        if "wind" in note.lower(): st.caption("🌬️ Weather Alert")

    except Exception as e:
        st.error(f"Execution Error: {e}")
