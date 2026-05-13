import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Load from Row 2 headers
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. CONFIG & UI ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # --- DYNAMIC COLUMN MAPPING ---
        # This prevents the "wrong column" issue by finding the headers by name
        def get_col(name_list, default_idx):
            for name in name_list:
                if name in df.columns:
                    return df[name]
            return df.iloc[:, default_idx]

        # Map metrics based on your previous corrections
        matchup = df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str)
        # Targeting Columns N & O for Sharp ML
        sharp_ml = df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str)
        sharp_dog = df.iloc[:, 15].astype(str)
        # Targeting Columns W & X for EV
        ev_vals = df.iloc[:, 22].astype(str) + " / " + df.iloc[:, 23].astype(str)
        picks = df.iloc[:, 25].astype(str) + " " + df.iloc[:, 26].astype(str)
        
        # Look for notes in Column AB or by name
        notes = get_col(["Tactical Note", "Notes", "Scouting"], 27).astype(str)

        master_table = pd.DataFrame({
            "Matchup": matchup,
            "Sharp ML %": sharp_ml,
            "Sharp Dog": sharp_dog,
            "EV (A/H)": ev_vals,
            "Model Pick": picks,
            "Raw_Notes": notes
        })

        # --- 3. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table.drop(columns=['Raw_Notes']), use_container_width=True, height=350)

        # --- 4. THE REPORT (Layout matching image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Detailed Scouting Notes")
            for _, row in master_table.iterrows():
                note_content = str(row['Raw_Notes']).strip()
                
                # If the sheet note is empty, we auto-generate the 'Why'
                if len(note_content) < 3:
                    ev_text = row['EV (A/H)']
                    ml_text = row['Sharp ML %']
                    note_content = f"Model identifies value on {row['Model Pick']} with an EV of {ev_text}. Sharp money flow is currently {ml_text}."
                
                st.info(f"**{row['Matchup']}**\n\n{note_content}")

    except Exception as e:
        st.error(f"Mapping Error: {e}. Check if your spreadsheet structure changed.")
else:
    st.info("🔄 Syncing with Google Sheets...")
