import streamlit as st
import pandas as pd

# --- 1. DATA SYNC ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=10)
def load_data():
    try:
        # Load from Row 2 headers
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. THE COLUMN DETECTIVE ---
def get_clean_col(df, target_names):
    """Finds a column by searching for keyword matches in headers."""
    for col in df.columns:
        if any(name.lower() in col.lower() for name in target_names):
            return df[col].astype(str)
    return pd.Series([""] * len(df))

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Explicit mapping by header name to prevent 'Handle' vs 'Vegas' mixups
        away = df.iloc[:, 0].astype(str)
        home = df.iloc[:, 1].astype(str)
        
        # We hunt for the exact data you need
        vegas_lines = get_clean_col(df, ["Vegas Lines", "Open Line", "Line"])
        sharp_ml = get_clean_col(df, ["Sharp ML %", "Sharp ML"])
        sharp_dog = get_clean_col(df, ["Sharp Dog"])
        ev_val = get_clean_col(df, ["EV", "Expected Value"]) # Corrected per EV request
        model_pick = get_clean_col(df, ["Model Pick", "Pick"])
        notes = get_clean_col(df, ["Tactical Note", "Notes", "Scouting"])

        master_table = pd.DataFrame({
            "Matchup": away + " @ " + home,
            "Vegas Lines": vegas_lines,
            "Sharp ML %": sharp_ml,
            "Sharp Dog": sharp_dog,
            "EV": ev_val,
            "Model Pick": model_pick,
            "Raw_Notes": notes
        })

        # --- 4. DISPLAY BOARD ---
        st.subheader("Live Tactical Board")
        st.dataframe(master_table.drop(columns=['Raw_Notes']), use_container_width=True, height=350)

        # --- 5. ALIGNMENT & SCOUTING ---
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
            st.markdown("### 📝 Scouting Notes")
            for _, row in master_table.iterrows():
                content = str(row['Raw_Notes']).strip()
                # If note column is empty, generate tactical summary from data
                if len(content) < 3:
                    content = f"Model identifies value on **{row['Model Pick']}** with an EV of **{row['EV']}**. Vegas opening: **{row['Vegas Lines']}**."
                
                st.info(f"**{row['Matchup']}**\n\n{content}")

    except Exception as e:
        st.error(f"Mapping Error: {e}")
else:
    st.info("🔄 Syncing with live data...")
