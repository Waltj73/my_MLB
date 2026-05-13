import streamlit as st
import pandas as pd

# --- 1. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. THE GENERATOR (If no notes exist in your sheet) ---
def generate_scouting_note(row):
    try:
        # Pulling your specific metrics: Sharp %, EV, and Model Pick
        sharp_v = str(row['Sharp ML %']).split('/')[0].strip()
        ev_val = str(row['EV (A/H)']).split('/')[0].strip()
        pick = str(row['Model Pick'])
        
        note = f"Analysis for {row['Matchup']}: "
        if "Away" in pick:
            note += f"Model shows value on the visitor with an EV of {ev_val}. "
        else:
            note += f"Home side is the target here. "
            
        if len(sharp_v) > 1 and "%" in sharp_v:
            note += f"Sharp money is currently sitting at {sharp_v} tracking institutional flow."
            
        return note
    except:
        return "Tactical data pending for this matchup."

# --- 3. UI CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Mapping your 2026 MLB data columns
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Sharp ML %": df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "EV (A/H)": df.iloc[:, 22].astype(str) + " / " + df.iloc[:, 23].astype(str),
            "Model Pick": df.iloc[:, 25].astype(str) + " " + df.iloc[:, 26].astype(str)
        })

        # --- 4. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(master_table, use_container_width=True, height=350)

        # --- 5. DYNAMIC REPORTS ---
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
            st.markdown("### 📝 Auto-Generated Scouting Notes")
            for _, row in master_table.iterrows():
                # Since there are no notes in the sheet, the script generates them here
                note_content = generate_scouting_note(row)
                st.info(f"**{row['Matchup']}**\n\n{note_content}")

    except Exception as e:
        st.error(f"Mapping Error: {e}")
else:
    st.info("🔄 Syncing with live data...")
