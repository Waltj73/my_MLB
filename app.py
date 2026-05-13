import streamlit as st
import pandas as pd

# 1. SETUP
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ MLB Data Command")

# 2. DATA SYNC
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Pulls data starting from Row 2 (headers)
        df = pd.read_csv(URL, skiprows=1).fillna('')
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    try:
        # Create the main table using specific column numbers (A=0, B=1, N=13, P=15, X=23, Z=25, AB=27)
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Market %": df.iloc[:, 13].astype(str),
            "Sharp Target": df.iloc[:, 15].astype(str),
            "Edge %": df.iloc[:, 23].astype(str),
            "Pick": df.iloc[:, 25].astype(str),
            "Notes": df.iloc[:, 27].astype(str) if df.shape[1] > 27 else ""
        })

        # --- TACTICAL BOARD ---
        st.subheader("Current Board")
        st.dataframe(master_table, use_container_width=True, height=400)

        # --- SIDE-BY-SIDE LAYOUT (MATCHING image_1e22b8.png) ---
        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 🎯 Alignment")
            for _, row in master_table.iterrows():
                target = str(row['Sharp Target']).strip()
                pick = str(row['Pick']).strip()
                if len(target) > 1 and target in pick:
                    st.success(f"**CONVICTION**: Model & Market on {target}")

        with col_right:
            st.markdown("### 📝 Scouting Notes")
            for _, row in master_table.iterrows():
                note = str(row['Notes']).strip()
                if len(note) > 3:
                    # Clean text block for the note
                    st.info(f"**{row['Matchup']}**: {note}")

    except Exception as e:
        st.error(f"Mapping Error: {e}")
else:
    st.info("Syncing...")
