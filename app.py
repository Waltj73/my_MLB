import streamlit as st
import pandas as pd

# --- 1. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=10)
def load_data():
    try:
        # skiprows=1 targets Row 2 where your actual headers live
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. DASHBOARD CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # --- THE HARDENED MAPPING ---
        # We find headers by name so it NEVER grabs the wrong data.
        def get_data(col_name):
            if col_name in df.columns:
                return df[col_name].astype(str)
            return pd.Series([""] * len(df))

        # Explicitly pulling the data points you need
        away = df.iloc[:, 0].astype(str)
        home = df.iloc[:, 1].astype(str)
        
        # Mapping by your specific header names
        vegas_lines = get_data("Vegas Lines")
        sharp_ml_away = get_data("Sharp ML %") # Adjusted to find the specific column
        sharp_dog = get_data("Sharp Dog")
        ev_val = get_data("EV") # Using the corrected EV mapping
        model_pick = get_data("Model Pick")
        tactical_notes = get_data("Tactical Note")

        master_table = pd.DataFrame({
            "Matchup": away + " @ " + home,
            "Vegas Lines": vegas_lines,
            "Sharp Dog": sharp_dog,
            "EV": ev_val,
            "Model Pick": model_pick,
            "Notes": tactical_notes
        })

        # --- 3. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table.drop(columns=['Notes']), use_container_width=True, height=350)

        # --- 4. ALIGNMENT & SCOUTING (Layout: image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = row['Sharp Dog'].strip()
                pick = row['Model Pick'].strip()
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Scouting Notes")
            for _, row in master_table.iterrows():
                note_text = row['Notes'].strip()
                # If note is empty, we auto-generate the 'Why' using EV and Pick
                if len(note_text) < 3:
                    note_text = f"Model identifies value on **{row['Model Pick']}**. Current EV is **{row['EV']}**."
                
                st.info(f"**{row['Matchup']}**\n\n{note_text}")

    except Exception as e:
        st.error(f"Mapping Error: {e}")
else:
    st.info("🔄 Syncing with live spreadsheet data...")
