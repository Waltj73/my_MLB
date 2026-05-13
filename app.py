import streamlit as st
import pandas as pd

# --- 1. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=5)
def load_data():
    try:
        # skiprows=1 pulls the Row 2 headers directly
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI CONFIG ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # --- THE FIX: HEADER-BASED MAPPING ---
        # This finds your data by name so 'Vegas Lines' never swaps with 'Handle'
        def get_col(name):
            return df[name].astype(str) if name in df.columns else pd.Series(["N/A"] * len(df))

        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Vegas Lines": get_col("Vegas Lines"),
            "Sharp ML %": get_col("Sharp ML %"),
            "Sharp Dog": get_col("Sharp Dog"),
            "EV": get_col("EV"),
            "Model Pick": get_col("Model Pick"),
            "Notes": get_col("Tactical Note")
        })

        # --- 3. DISPLAY BOARD ---
        st.subheader("Live Tactical Board")
        st.dataframe(master_table.drop(columns=['Notes']), use_container_width=True, height=350)

        # --- 4. ALIGNMENT & SCOUTING (Matching your layout) ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if s_dog != "N/A" and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Scouting Notes")
            for _, row in master_table.iterrows():
                content = str(row['Notes']).strip()
                # If note is empty, we auto-generate the 'Why' using your EV and Vegas Lines
                if len(content) < 3 or content == "N/A":
                    content = f"Model identifies value on **{row['Model Pick']}** with an EV of **{row['EV']}**. Vegas Line: **{row['Vegas Lines']}**."
                
                st.info(f"**{row['Matchup']}**\n\n{content}")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with live spreadsheet data...")
