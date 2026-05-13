import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st_autorefresh(interval=60 * 1000, key="sheet_heartbeat") # Auto-syncs every minute

# --- 2. YOUR CONNECTION ---
# PASTE YOUR SHEET ID HERE
SHEET_ID = 'your_long_id_here' 
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'

# --- 3. THE LIVE SYNC ---
st.title("⚾ MLB Intelligence: Direct Sync")
st.caption(f"Last Refresh: {pd.Timestamp.now().strftime('%H:%M:%S')}")

try:
    # Directly pulls your sheet data exactly as it looks in Google
    df = pd.read_csv(url)
    
    if not df.empty:
        # High-intensity styling for the trade edge
        def highlight_edge(val):
            try:
                num = float(val)
                # Green for high value, Red for bad value
                color = '#27ae60' if num > 12 else ('#c0392b' if num < -10 else '')
                return f'background-color: {color}; color: white'
            except:
                return ''

        # Displaying the board
        st.dataframe(
            df.style.applymap(highlight_edge, subset=['EV'] if 'EV' in df.columns else []),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Sheet connected but no data found.")

except Exception as e:
    st.error("Connection Failed. Check that your sheet is set to 'Anyone with the link can view'.")
