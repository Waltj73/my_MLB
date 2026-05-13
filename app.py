import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Pulls data from Row 2 (the headers)
        df = pd.read_csv(URL, skiprows=1).fillna('')
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. LAYOUT & DISPLAY ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Mapping columns: A/B(Teams), N/O(Sharp%), P(SharpDog), X(EV), Z/AA(Pick), AB(Notes)
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Vegas Odds": df.iloc[:, 4].astype(str) + " / " + df.iloc[:, 5].astype(str),
            "Sharp ML %": df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "Win %": df.iloc[:, 18].astype(str) + " / " + df.iloc[:, 19].astype(str),
            "EV (A/H)": df.iloc[:, 22].astype(str) + " / " + df.iloc[:, 23].astype(str),
            "Model Pick": df.iloc[:, 25].astype(str) + " " + df.iloc[:, 26].astype(str),
            "Tactical Note": df.iloc[:, 27].astype(str) if df.shape[1] > 27 else ""
        })

        # --- TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table, use_container_width=True, height=400)

        # --- 3. THE DETAILED REPORT (Matching image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                # Display green conviction boxes
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Detailed Scouting Notes")
            for _, row in master_table.iterrows():
                note = str(row['Tactical Note']).strip()
                if len(note) > 3:
                    # Display the full, detailed note for every matchup that has one
                    st.info(f"**{row['Matchup']}**\n\n{note}")
                else:
                    # Clear indicator if a game is missing expected details
                    st.caption(f"No detailed notes yet for {row['Matchup']}")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("Syncing with Google Sheets...")
