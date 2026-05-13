import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & HEARTBEAT ---
st.set_page_config(page_title="MLB Intelligence Engine", layout="wide")
st_autorefresh(interval=60 * 1000, key="mlb_sync")

# --- 2. YOUR DATA SOURCE ---
# Using the direct export link for your 'Model' tab
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'

# --- 3. THE DATA ENGINE ---
try:
    # We skip the first 2 rows of your sheet to get to the real headers (Away Team, Home Team, etc.)
    df = pd.read_csv(url, skiprows=2)
    
    # Cleaning: Removing any empty rows or columns that often appear in export
    df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)

    st.title("⚾ MLB Intelligence Dashboard")
    st.caption(f"LIVE SYNC ACTIVE | Last Refresh: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # --- 4. THE VISUAL BOARD ---
    # Highlighting your EV Edge (e.g., Colorado at 21.08 or Pittsburgh at -68.69)
    def highlight_ev(val):
        try:
            num = float(val)
            color = '#27ae60' if num > 12 else ('#c0392b' if num < -10 else '')
            return f'background-color: {color}; color: white'
        except:
            return ''

    # We only show the columns you need for the decision
    # These match your headers: 'Away Team', 'Home Team', 'EV', 'Sharp', etc.
    display_cols = ['Away Team', 'Home Team', 'Vegas Win%', 'My Win%', 'EV', 'Sharp']
    # Filter for columns that actually exist in the data pull
    final_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[final_cols].style.applymap(highlight_edge, subset=['EV'] if 'EV' in df.columns else []),
        use_container_width=True,
        hide_index=True
    )

    # --- 5. ALERTS ---
    # Calling out the Sharp action you've tracked (e.g., Colorado at 16.0% Sharps ML)
    if 'Sharp' in df.columns:
        sharps = df[pd.to_numeric(df['Sharp'], errors='coerce').abs() > 15]
        if not sharps.empty:
            st.divider()
            st.subheader("🔥 High-Priority Sharp Alerts")
            for _, row in sharps.iterrows():
                st.warning(f"**{row['Away Team']}**: {row['Sharp']}% Sharp Action Detected")

except Exception as e:
    st.error(f"Sync Error: {e}. Ensure the sheet is still shared as 'Anyone with the link can view'.")
