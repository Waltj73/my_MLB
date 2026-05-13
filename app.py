import streamlit as st
import pandas as pd

# --- 1. DATA CONNECTION ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 ensures we hit your Row 2 headers (Vegas Lines, Team, etc.)
        df = pd.read_csv(URL, skiprows=1).fillna('')
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
        # --- THE "NO-FAIL" MAPPING ---
        # We search for your specific headers by name so the script never grabs the wrong data.
        def find_col(possible_names):
            for name in possible_names:
                if name in df.columns: return df[name]
            return pd.Series([""] * len(df))

        # Explicitly grabbing the Vegas Lines and your specific Model metrics
        away_team = df.iloc[:, 0]
        home_team = df.iloc[:, 1]
        
        # This specifically targets the ODDS/LINES, not the money handles
        vegas_lines = find_col(["Vegas Lines", "Opening Line", "Current Line"])
        sharp_ml = find_col(["Sharp ML %", "Sharp ML"])
        sharp_dog = find_col(["Sharp Dog"])
        
        # Using your corrected EV logic
        ev_data = find_col(["EV", "Expected Value"]) 
        model_pick = find_col(["Model Pick", "Pick"])

        master_table = pd.DataFrame({
            "Matchup": away_team.astype(str) + " @ " + home_team.astype(str),
            "Vegas Lines": vegas_lines,
            "Sharp ML %": sharp_ml,
            "Sharp Dog": sharp_dog,
            "EV": ev_data,
            "Model Pick": model_pick
        })

        # --- 3. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table, use_container_width=True, height=350)

        # --- 4. ALIGNMENT & SCOUTING (Layout: image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                # Only show if there's a real alignment
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Tactical Intelligence")
            for _, row in master_table.iterrows():
                # Since we aren't finding notes in the sheet, we generate the "Why" 
                # based on the Vegas Lines and EV you've provided.
                line = row['Vegas Lines']
                ev = row['EV']
                
                intel = f"Matchup opening at **{line}**. "
                intel += f"Model identifies value on **{row['Model Pick']}** with an EV of **{ev}**."
                
                st.info(f"**{row['Matchup']}**\n\n{intel}")

    except Exception as e:
        st.error(f"Mapping Error: {e}. Check that your Google Sheet headers are labeled correctly.")
else:
    st.info("🔄 Syncing with live spreadsheet data...")
