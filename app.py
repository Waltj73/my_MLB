import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & AUTO-SYNC ---
st.set_page_config(page_title="MLB Intelligence Engine", layout="wide")
st_autorefresh(interval=60 * 1000, key="mlb_sync_fix")

# --- 2. YOUR SOURCE DATA ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'

# --- 3. THE LIVE ENGINE ---
st.title("⚾ MLB Intelligence Dashboard")
st.caption(f"SYNC ACTIVE | Last Refresh: {pd.Timestamp.now().strftime('%H:%M:%S')}")

try:
    # Skip the top labels to get to 'Away Team' and 'Home Team'
    df = pd.read_csv(url, skiprows=2)
    
    # Isolate the active model rows (top 15)
    df = df.iloc[:15].copy() 

    # Clean numeric columns for your EV and Sharp calculations
    cols_to_fix = ['EV', 'Sharp', 'My Win%', 'Vegas Win%']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 4. THE VISUAL BOARD ---
    def color_coding(val):
        try:
            num = float(val)
            # High-intensity green for edges > 12
            color = '#27ae60' if num > 12 else ('#c0392b' if num < -10 else '')
            return f'background-color: {color}; color: white'
        except:
            return ''

    # Filter for your decision metrics
    display_cols = ['Away Team', 'Home Team', 'Vegas Win%', 'My Win%', 'EV', 'Sharp']
    final_view = [c for c in display_cols if c in df.columns]

    st.subheader("📋 Active Market Edge")
    
    # FIXED LINE: Changed .applymap to .map for newer Pandas versions
    st.dataframe(
        df[final_view].style.map(color_coding, subset=['EV'] if 'EV' in df.columns else []),
        use_container_width=True,
        hide_index=True
    )

    # --- 5. SHARP ALERTS ---
    # Tracking moves like the 16% Sharp action on Colorado
    if 'Sharp' in df.columns:
        sharps = df[df['Sharp'].abs() > 15]
        if not sharps.empty:
            st.divider()
            st.subheader("🔥 Priority Sharp Alerts")
            for _, row in sharps.iterrows():
                st.warning(f"**{row['Away Team']}**: {row['Sharp']}% Sharp Divergence")

except Exception as e:
    st.error(f"Sync Status: Connection Pending... ({e})")
