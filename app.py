import streamlit as st
import pandas as pd

# --- 1. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Pull data starting from Row 2 headers
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. THE "WHY" GENERATOR (Failsafe) ---
def generate_tactical_intel(row):
    try:
        pick = str(row.get('Model Pick', 'N/A')).strip()
        ev_val = str(row.get('EV (A/H)', 'N/A')).strip()
        intel = f"Model identifies high-conviction value on **{pick}**. "
        intel += f"Current Expected Value (EV) is calculated at **{ev_val}**."
        return intel
    except:
        return "Tactical data stream active. Awaiting market updates."

# --- 3. UI CONFIG ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # SAFE COLUMN MAPPING: This prevents "out-of-bounds" errors
        # It looks for the name first; if missing, it uses a safe empty default.
        def safe_get(df, index, fallback_name):
            if fallback_name in df.columns:
                return df[fallback_name]
            if len(df.columns) > index:
                return df.iloc[:, index]
            return pd.Series([""] * len(df))

        # Reconstructing the table using your specific metrics
        processed_data = pd.DataFrame({
            "Matchup": safe_get(df, 0, "Away Team").astype(str) + " @ " + safe_get(df, 1, "Home Team").astype(str),
            "Sharp ML % (A/H)": safe_get(df, 13, "Sharp ML %").astype(str) + " / " + safe_get(df, 14, "Sharp ML %").astype(str),
            "Sharp Dog": safe_get(df, 15, "Sharp Dog"),
            "EV (A/H)": safe_get(df, 22, "EV").astype(str) + " / " + safe_get(df, 23, "EV").astype(str),
            "Model Pick": safe_get(df, 25, "Pick Team").astype(str) + " " + safe_get(df, 26, "Pick Value").astype(str),
            "Sheet_Notes": safe_get(df, 27, "Tactical Note")
        })

        # --- 4. TACTICAL BOARD ---
        st.subheader("Tactical Board")
        st.dataframe(processed_data.drop(columns=['Sheet_Notes']), use_container_width=True, height=350)

        # --- 5. ALIGNMENT & SCOUTING (Layout: image_1e22b8.png) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in processed_data.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1 and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Detailed Scouting Notes")
            for _, row in processed_data.iterrows():
                sheet_note = str(row['Sheet_Notes']).strip()
                # If note column is missing or empty, generate intel automatically
                display_note = sheet_note if len(sheet_note) > 3 else generate_tactical_intel(row)
                st.info(f"**{row['Matchup']}**\n\n{display_note}")

    except Exception as e:
        st.error(f"Mapping Error: {e}. Ensure the 'Model' tab headers haven't been deleted.")
else:
    st.info("🔄 Syncing with live data...")
