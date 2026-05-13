import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
# 15-second refresh for live trading data
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 ensures we hit the 'Away Team' / 'Home Team' headers
        df = pd.read_csv(URL, skiprows=1).fillna('')
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Index Safety: Check if Column AB (Index 27) exists
        col_count = df.shape[1]
        
        # Mapping for the Tactical Board
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Vegas Odds": df.iloc[:, 4].astype(str) + " / " + df.iloc[:, 5].astype(str),
            "Sharp ML %": df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "Win %": df.iloc[:, 18].astype(str) + " / " + df.iloc[:, 19].astype(str),
            "EV (A/H)": df.iloc[:, 22].astype(str) + " / " + df.iloc[:, 23].astype(str),
            "Model Pick": df.iloc[:, 25].astype(str) + " " + df.iloc[:, 26].astype(str),
            "Tactical Note": df.iloc[:, 27].astype(str) if col_count > 27 else ""
        })

        # --- 3. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table, use_container_width=True, height=400)

        # --- 4. ALIGNMENT & NOTES (Matching image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                # Renders the green conviction boxes
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Scouting Notes (The 'Why')")
            for _, row in master_table.iterrows():
                note = str(row['Tactical Note']).strip()
                # Only display if there is a real note (more than 3 characters)
                if len(note) > 3:
                    st.info(f"**{row['Matchup']}**: {note}")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets...")
