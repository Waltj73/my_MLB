import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
# Targeting the "Model" tab with a 15-second refresh for live trading
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 aligns the headers with your data structure
        df = pd.read_csv(URL, skiprows=1).fillna('')
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. LAYOUT CONFIGURATION ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Standardize empty values to prevent layout breaks
        df = df.fillna('')
        
        # Mapping for the Tactical Board (A, B, E, F, N, O, P, S, T, W, X, Z, AA, AB)
        # 0:Away, 1:Home, 4/5:Odds, 13/14:Sharp%, 15:SharpDog, 18/19:Win%, 22/23:EV, 25/26:Pick, 27:Notes
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

        # --- 3. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        
        # High-contrast highlighting for Scalping 
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

        # --- 4. ALIGNMENT & DETAILED NOTES (LAYOUT MATCHING image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                # Display Green Conviction Boxes
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Scouting Notes (The 'Why')")
            for _, row in master_table.iterrows():
                # This pulls the full text from Column AB (index 27)
                note = str(row['Tactical Note']).strip()
                if len(note) > 3:
                    st.info(f"**{row['Matchup']}**\n\n{note}")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets 'Model' tab...")
