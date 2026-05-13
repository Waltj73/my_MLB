import streamlit as st
import pandas as pd
import cloudscraper
from streamlit_autorefresh import st_autorefresh

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="MLB Betting Edge: Live VSiN", layout="wide")

# Refresh the app every 2 minutes to get fresh VSiN data
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# --- 2. DATA FETCHING FUNCTION ---
@st.cache_data(ttl=120)
def fetch_live_data():
    """
    Fetches live MLB data. 
    Note: Replace the URL/Logic below with your specific VSiN JSON endpoint 
    found in your browser's network tab.
    """
    scraper = cloudscraper.create_scraper()
    
    try:
        # Placeholder for the actual VSiN JSON endpoint
        # vsin_url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        # response = scraper.get(vsin_url)
        # data = response.json()
        
        # --- SIMULATED DATA (Matches your May 13 slate) ---
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
        df['My Win% Home'] = 100 - df['My Win% Away']
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- 3. CALCULATION ENGINE ---
def calculate_ev(win_pct, ml):
    """Calculates EV: (Win% * Payout) - Loss%"""
    if ml > 0:
        payout = ml / 100
    else:
        payout = 100 / abs(ml)
    return ((win_pct / 100) * payout) - ((100 - win_pct) / 100)

# --- 4. EXECUTION FLOW ---
# Define variables before UI logic to avoid NameErrors
df = fetch_live_data()

if not df.empty:
    # Calculations
    df['EV Away'] = df.apply(lambda x: calculate_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
    df['EV Home'] = df.apply(lambda x: calculate_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)
    df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']

    # --- 5. UI LAYOUT ---
    st.title("⚾ MLB Betting Edge: Live VSiN Feed")
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # SECTION: FULL SLATE
    st.header("📋 Full Slate")
    
    def style_ev(val):
        """Matches your sheet shading: Dark Green > 8%, Light Green > 0%, Red < -5%"""
        if val > 0.08: return 'background-color: #2ecc71; color: black;'
        elif val > 0: return 'background-color: #d5f5e3; color: black;'
        elif val < -0.05: return 'background-color: #f5b7b1; color: black;'
        return ''

    st.dataframe(
        df.style.map(style_ev, subset=['EV Away', 'EV Home']),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # SECTION: TOP PLAYS (Thresholds: EV > 5% OR Sharp Diff > 15%)
    st.header("🎯 Top Plays & Sharp Moves")
    
    top_plays = df[
        (df['EV Away'] > 0.05) | 
        (df['EV Home'] > 0.05) | 
        (abs(df['Sharp Diff']) > 15)
    ].copy()

    if not top_plays.empty:
        top_plays['Pick'] = top_plays.apply(
            lambda x: x['Away'] if x['EV Away'] > x['EV Home'] else x['Home'], axis=1
        )
        st.table(top_plays[['Away', 'Home', 'Pick', 'EV Away', 'EV Home', 'Sharp Diff']])
    else:
        st.write("No edges detected. Watching market for movement...")
else:
    st.warning("Awaiting data from VSiN feed...")
