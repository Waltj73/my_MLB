import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION ---
# This is your source of truth. The CSV export link for your "Model" tab.
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

# --- DATA ENGINE ---
@st.cache_data(ttl=5) # Refresh every 5 seconds for scalping/live updates
def load_live_data():
    try:
        # skiprows=1 targets Row 2 where your actual headers (Vegas Lines, EV, etc.) live
        df = pd.read_csv(URL, skiprows=1).fillna('')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- UI SETUP ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide", initial_sidebar_state="collapsed")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_live_data()

if not df.empty:
    try:
        # --- THE TRANSLATOR: HEADER-BASED MAPPING ---
        # This function finds your data by NAME so it never grabs 'Handle' instead of 'Vegas'
        def get_col(name):
            if name in df.columns:
                return df[name].astype(str)
            return pd.Series(["N/A"] * len(df))

        # Building the Master Table from your spreadsheet cells
        master_table = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Vegas Lines": get_col("Vegas Lines"),
            "Sharp ML %": get_col("Sharp ML %"),
            "Sharp Dog": get_col("Sharp Dog"),
            "EV": get_col("EV"),
            "Model Pick": get_col("Model Pick"),
            "Notes": get_col("Tactical Note")
        })

        # --- TACTICAL BOARD ---
        st.subheader("Live Market Feed")
        st.dataframe(
            master_table.drop(columns=['Notes']), 
            use_container_width=True, 
            height=400,
            hide_index=True
        )

        # --- ANALYSIS PANELS ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                # Highlight if Sharps and Model agree on the same team
                if s_dog != "N/A" and s_dog != "" and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")

        with col_r:
            st.markdown("### 📝 Detailed Scouting Notes")
            for _, row in master_table.iterrows():
                content = str(row['Notes']).strip()
                # Failsafe: If you haven't written a note, Python writes the 'Why' for you
                if len(content) < 3 or content == "N/A":
                    content = f"Model identifies value on **{row['Model Pick']}** with an EV of **{row['EV']}**. Vegas Line is currently **{row['Vegas Lines']}**."
                
                st.info(f"**{row['Matchup']}**\n\n{content}")

    except Exception as e:
        st.error(f"Logic Error: {e}. Check that Row 2 headers match exactly.")
else:
    st.info("🔄 Syncing with live spreadsheet data...")
