import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & AUTO-SYNC ---
st.set_page_config(page_title="MLB Intelligence Engine", layout="wide")
# This auto-refreshes the dashboard every 60 seconds to catch your sheet updates
st_autorefresh(interval=60 * 1000, key="mlb_sync_heartbeat")

# --- 2. YOUR SOURCE DATA ---
# This is the direct ID from the link you provided
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# We use the direct CSV export link to bypass Google's login screen
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'

# --- 3. THE LIVE ENGINE ---
st.title("⚾ MLB Intelligence Dashboard")
st.caption(f"CONNECTED TO: 2026 MLB Model | Last Sync: {pd.Timestamp.now().strftime('%H:%M:%S')}")

try:
    # CRITICAL: We skip exactly 2 rows so Python starts reading at 'Away Team'
    df = pd.read_csv(url, skiprows=2)
    
    # We stop reading once we hit the empty rows before your 'Matchups' section
    # This keeps the dashboard clean and focused only on the active model
    df = df.iloc[:15] 

    # Convert the columns you care about to numbers so we can color-code them
    cols_to_fix = ['EV', 'Sharp', 'My Win%', 'Vegas Win%']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 4. THE VISUAL BOARD ---
    # Highlighting the EV Edge (e.g., Pittsburgh at 21.08)
    def color_coding(val):
        try:
            num = float(val)
            # High-intensity green for the big edges you look for
            color = '#27ae60' if num > 12 else ('#c0392b' if num < -10 else '')
            return f'background-color: {color}; color: white'
        except:
            return ''

    # Selecting your primary decision metrics
    display_cols = ['Away Team', 'Home Team', 'Vegas Win%', 'My Win%', 'EV', 'Sharp']
    final_view = [c for c in display_cols if c in df.columns]

    st.subheader("📋 Active Market Edge")
    st.dataframe(
        df[final_view].style.applymap(color_coding, subset=['EV'] if 'EV' in df.columns else []),
        use_container_width=True,
        hide_index=True
    )

    # --- 5. SHARP ALERTS ---
    # This calls out the big moves, like the 16% Sharp action on Colorado
    if 'Sharp' in df.columns:
        sharps = df[df['Sharp'].abs() > 15]
        if not sharps.empty:
            st.divider()
            st.subheader("🔥 Priority Sharp Alerts")
            for _, row in sharps.iterrows():
                st.warning(f"**{row['Away Team']}**: {row['Sharp']}% Sharp Divergence")

except Exception as e:
    st.error(f"Waiting for Data... (Technical Note: {e})")
