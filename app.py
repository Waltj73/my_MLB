import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 1. Setup & Auto-Refresh (Every 2 minutes)
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# 2. Data Fetching (Full Slate for May 13, 2026)
@st.cache_data(ttl=120)
def fetch_live_data():
    # In your live version, this replaces the simulation with your VSiN Scraper
    # Representing the full slate of 15 games
    data = {
        "Away": ["Angels", "Yankees", "Nationals", "Rockies", "Phillies", "Rays", "Tigers", "Cubs", "Royals", "Marlins", "Padres", "D-Backs", "Mariners", "Cardinals", "Giants"],
        "Home": ["Guardians", "Orioles", "Reds", "Pirates", "Red Sox", "Blue Jays", "Mets", "Braves", "White Sox", "Twins", "Brewers", "Rangers", "Astros", "Athletics", "Dodgers"],
        "Vegas ML Away": [135, -173, 139, 153, 109, 135, -108, -136, -115, -126, 129, 102, -126, 123, 199],
        "Vegas ML Home": [-163, 142, -168, -186, -131, -163, -112, 113, -105, 104, -156, -122, 104, -149, -246],
        "Handle% Away": [5, 99, 21, 8, 29, 23, 71, 54, 75, 81, 4, 27, 67, 65, 7],
        "Bets% Away": [34, 91, 57, 23, 60, 56, 38, 37, 35, 35, 38, 25, 54, 66, 25],
        "My Win% Away": [35.0, 65.0, 42.0, 30.0, 52.0, 45.0, 55.0, 60.0, 51.0, 58.0, 40.0, 50.0, 58.0, 48.0, 30.0],
    }
    df = pd.DataFrame(data)
    # Calculate Home Win% as remainder
    df['My Win% Home'] = 100 - df['My Win% Away']
    return df

# 3. Calculation Engine
def get_ev(win_pct, ml):
    payout = ml / 100 if ml > 0 else 100 / abs(ml)
    return round(((win_pct / 100) * payout) - ((100 - win_pct) / 100), 3)

df = fetch_live_data()
df['EV Away'] = df.apply(lambda x: get_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
df['EV Home'] = df.apply(lambda x: get_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)
df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']

# --- STYLING ---
def color_ev(val):
    color = '#2ecc71' if val > 0.10 else '#f1948a' if val < -0.10 else ''
    return f'background-color: {color}'

# --- LAYOUT ---
st.title("⚾ MLB Betting Edge: Live VSiN Feed")

# SECTION 1: FULL SLATE
st.header("📋 Full Slate - All Games")
st.dataframe(
    df.style.map(color_ev, subset=['EV Away', 'EV Home']),
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# SECTION 2: TOP PLAYS
st.header("🎯 Top Plays (10%+ Edge)")

# Filter for games where either Away or Home has a > 10% EV
top_plays = df[(df['EV Away'] > 0.10) | (df['EV Home'] > 0.10)].copy()

if not top_plays.empty:
    # Highlight the specific side that is the "Pick"
    top_plays['Recommended Side'] = top_plays.apply(
        lambda x: x['Away'] if x['EV Away'] > x['EV Home'] else x['Home'], axis=1
    )
    
    st.table(top_plays[['Away', 'Home', 'Recommended Side', 'EV Away', 'EV Home']])
else:
    st.write("No high-value edges detected at this refresh.")

st.caption(f"Last sync: {pd.Timestamp.now().strftime('%H:%M:%S')} | Data Source: VSiN Live")
