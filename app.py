import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG ---
st.set_page_config(page_title="Institutional Edge Scanner", layout="wide")
st_autorefresh(interval=60 * 1000, key="edge_scanner")

# --- 2. THE DATA SOURCE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# Target the 'Matchups' tab specifically
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matchups'

st.title("🏹 Institutional Edge Scanner")
st.caption(f"Targeting: Matchups Tab | Live Sync: {pd.Timestamp.now().strftime('%H:%M:%S')}")

try:
    # Read and clean the Matchups data
    df = pd.read_csv(url)
    
    # We find the core columns: Away Team, Home Team, EV, and Sharp
    # We filter only for games that meet your 'Professional' thresholds
    df['EV_Num'] = pd.to_numeric(df['EV'], errors='coerce').fillna(0)
    df['Sharp_Num'] = pd.to_numeric(df['Sharp'], errors='coerce').fillna(0)

    # LOGIC: The "High Conviction" Signal
    # Only show games where:
    # 1. EV is over 12 (Your Model Edge)
    # 2. Sharp Action is over 10% (Market Confirmation)
    high_conviction = df[(df['EV_Num'].abs() > 12) & (df['Sharp_Num'].abs() > 10)].copy()

    if not high_conviction.empty:
        st.subheader("🔥 High Conviction Signals")
        st.write("Alignment between Model EV and Sharp Money detected.")
        
        # We calculate a 'Conviction Score' (EV + Sharp strength)
        high_conviction['Conviction'] = (high_conviction['EV_Num'].abs() + high_conviction['Sharp_Num'].abs()) / 2
        
        # Displaying only the "Action" items
        display = high_conviction[['Away Team', 'Home Team', 'EV', 'Sharp', 'Conviction']]
        
        st.dataframe(
            display.style.background_gradient(cmap='Greens', subset=['Conviction']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Scanning for institutional flow... No high-conviction alignments found at this moment.")

    # --- 3. SYSTEM ALERTS ---
    # Instant notification if a 'Sharp' move hits your 15% threshold
    extreme_moves = df[df['Sharp_Num'].abs() >= 15]
    if not extreme_moves.empty:
        st.divider()
        st.subheader("⚠️ Extreme Sharp Alerts")
        for _, row in extreme_moves.iterrows():
            st.error(f"**{row['Away Team']}**: {row['Sharp']}% Sharp Action (Extreme Divergence)")

except Exception as e:
    st.error(f"Searching for data in Matchups... {e}")
