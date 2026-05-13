import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 1. Setup & Auto-Refresh
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# 2. Replicating Your Formula Logic
def calculate_ev(win_pct, ml):
    """Calculates EV: (Win% * Payout) - Loss%"""
    if ml > 0:
        payout = ml / 100
    else:
        payout = 100 / abs(ml)
    # Result is a decimal (e.g., 0.05 for 5%)
    return ((win_pct / 100) * payout) - ((100 - win_pct) / 100)

# 3. Data Processing
# This now pulls the full slate and applies your thresholds
df = fetch_live_data() # Using your VSiN data fetcher

# Apply EV calculations
df['EV Away'] = df.apply(lambda x: calculate_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
df['EV Home'] = df.apply(lambda x: calculate_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)

# Sharp Logic: Handle % vs Bets % difference
df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']

# --- NEW PICK LOGIC (Matching your sheet's thresholds) ---
# A 'Top Play' is now defined by EV > 0 OR Sharp Diff > 15
top_plays = df[
    (df['EV Away'] > 0.05) | 
    (df['EV Home'] > 0.05) | 
    (abs(df['Sharp Diff']) > 15)
].copy()

# --- STYLING (Matching your Conditional Formatting) ---
def style_table(val):
    if val > 0.08: # Green for strong edges
        return 'background-color: #2ecc71; color: black;'
    elif val > 0: # Light green for any positive value
        return 'background-color: #d5f5e3; color: black;'
    elif val < -0.05: # Red for negative value
        return 'background-color: #f5b7b1; color: black;'
    return ''

# --- UI LAYOUT ---
st.title("⚾ MLB Betting Edge Dashboard")

## Full Slate
st.subheader("📋 All Games")
st.dataframe(
    df.style.map(style_table, subset=['EV Away', 'EV Home']),
    use_container_width=True,
    hide_index=True
)

st.divider()

## Top Plays Section
st.subheader("🎯 Top Plays & Sharp Moves")
if not top_plays.empty:
    # Identify which side the "Pick" is on
    top_plays['Pick'] = top_plays.apply(
        lambda x: x['Away'] if x['EV Away'] > x['EV Home'] else x['Home'], axis=1
    )
    st.table(top_plays[['Away', 'Home', 'Pick', 'EV Away', 'EV Home', 'Sharp Diff']])
else:
    st.write("Monitoring market for new edges...")
