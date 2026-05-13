import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 is standard if Row 1 is a title/blank and Row 2 has headers
        df = pd.read_csv(URL, skiprows=1).fillna('')
        # Clean header names for matching
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

# --- DEBUG TOOL (Optional check if notes still don't appear) ---
if st.sidebar.checkbox("Show Column Map"):
    st.sidebar.write(list(enumerate(df.columns)))

if not df.empty:
    try:
        # Direct Mapping for the Tactical Board
        # Using iloc ensures it works even if headers are slightly named differently
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Vegas Odds": df.iloc[:, 4].astype(str) + " / " + df.iloc[:, 5].astype(str),
            "Sharp ML %": df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "Win %": df.iloc[:, 18].astype(str) + " / " + df.iloc[:, 19].astype(str),
            "EV (A/H)": df.iloc[:, 22].astype(str) + " / " + df.iloc[:, 23].astype(str),
            "Model Pick": df.iloc[:, 25].astype(str) + " " + df.iloc[:, 26].astype(str),
            "Detailed Note": df.iloc[:, 27].astype(str) if df.shape[1] > 27 else ""
        })

        # Display Table
        st.subheader("Tactical Board")
        st.dataframe(master_table, use_container_width=True, height=400)

        # --- 3. ALIGNMENT & NOTES (MATCHING image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            alignment_found = False
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")
                    alignment_found = True
            if not alignment_found:
                st.caption("No direct Sharp/Model alignments at this time.")

        with col_r:
            st.markdown("### 📝 Scouting Notes (The 'Why')")
            notes_found = False
            for _, row in master_table.iterrows():
                note_text = str(row['Detailed Note']).strip()
                # If there's content in Column AB (Index 27), display it
                if len(note_text) > 2:
                    st.info(f"**{row['Matchup']}**\n\n{note_text}")
                    notes_found = True
            
            if not notes_found:
                st.warning("⚠️ No detailed notes found in Column AB. Check sheet alignment.")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets...")

# INSTRUCTIONS:
# 1. If notes aren't showing, check "Show Column Map" in the sidebar.
# 2. Match the number for your notes column to the '27' in df.iloc[:, 27].
