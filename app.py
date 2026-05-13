import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 aligns headers with 'Away Team' / 'Home Team' (Row 2 in sheet)
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
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
        df = df.fillna('')
        
        # Filter for active game rows
        main_df = df[df.iloc[:, 0].astype(str).str.len() > 2].copy()

        # --- 3. MAPPING (A-AB Columns) ---
        # A,B(0,1) | E,F(4,5) | N,O(13,14) | P(15) | S,T(18,19) | W,X(22,23) | Z,AA(25,26) | AB(27)
        master_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "Sharp ML %": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Dog": main_df.iloc[:, 15].astype(str),
            "Win %": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (A/H)": main_df.iloc[:, 22].astype(str) + " / " + main_df.iloc[:, 23].astype(str),
            "Model Pick": main_df.iloc[:, 25].astype(str) + " " + main_df.iloc[:, 26].astype(str),
            "Tactical Note": main_df.iloc[:, 27].astype(str) if main_df.shape[1] > 27 else ""
        })

        # --- 4. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            if len(str(row['Sharp Dog']).strip()) > 1:
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            if len(str(row['Model Pick']).strip()) > 1:
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(
            master_table.style.apply(highlight_logic, axis=1),
            use_container_width=True,
            height=400
        )

        # --- 5. ALIGNMENT & NOTES (MATCHING image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1 and s_dog in pick:
                    # Direct success block to match image_1e22b8.png
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Scouting Notes (The 'Why')")
            for _, row in master_table.iterrows():
                note = str(row['Tactical Note']).strip()
                if len(note) > 3:
                    # Info block used to provide visual separation matching the left side
                    st.info(f"**{row['Matchup']}**: {note}")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets...")
