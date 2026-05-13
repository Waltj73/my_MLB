import streamlit as st
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & AUTO-SYNC ---
st.set_page_config(page_title="MLB Intelligence Engine", layout="wide")
# Syncs with your Google Sheet every 60 seconds
st_autorefresh(interval=60 * 1000, key="sheet_heartbeat")

# --- 2. YOUR SOURCE DATA ---
# This ID matches your '2026 MLB Model' spreadsheet
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# We target the 'Model' gid or use the direct export link
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'

# --- 3. THE LIVE ENGINE ---
st.title("⚾ MLB Intelligence Command Center")
st.caption(f"LIVE SPREADSHEET SYNC | Last Heartbeat: {pd.Timestamp.now().strftime('%H:%M:%S')}")

try:
    # Pulling the raw data from your sheet
    raw_df = pd.read_csv(url)
    
    # We clean the columns to match your exact headers: 'Away Team', 'Home Team', 'EV', 'Sharp'
    # Your sheet uses multi-row headers, so we grab the core data rows
    df = raw_df.iloc[1:].copy() 
    
    # Convert core metrics to numbers for the dashboard
    # Mapping to your 'EV' and 'Sharp' columns
    cols_to_fix = ['EV', 'Sharp', 'My Win%', 'Vegas Win%']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 4. DASHBOARD VIEW ---
    # Highlighting the EV Edge just like your sheet logic
    def color_edge(val):
        try:
            num = float(val)
            # High-intensity Green for EV > 12, Red for negative value
            color = '#27ae60' if num > 12 else ('#c0392b' if num < -10 else '')
            return f'background-color: {color}; color: white'
        except:
            return ''

    # Filter for the view you need to make decisions
    view_cols = ['Away Team', 'Home Team', 'Vegas Win%', 'My Win%', 'EV', 'Sharp']
    available_cols = [c for c in view_cols if c in df.columns]
    
    st.subheader("📋 Market Edge & Sharp Action")
    st.dataframe(
        df[available_cols].style.applymap(color_edge, subset=['EV'] if 'EV' in df.columns else []),
        use_container_width=True,
        hide_index=True
    )

    # ALERTS: Triggered by your Sharp ML/Total logic
    if 'Sharp' in df.columns:
        alerts = df[abs(df['Sharp']) > 15]
        if not alerts.empty:
            st.divider()
            st.subheader("🔥 High-Priority Sharp Alerts")
            for _, row in alerts.iterrows():
                st.warning(f"**{row['Away Team']}**: {row['Sharp']}% Sharp Divergence detected.")

except Exception as e:
    st.error("Connection Interrupted. Please ensure your Google Sheet is set to 'Anyone with the link can view'.")
