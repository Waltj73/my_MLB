import streamlit as st
import pandas as pd
import numpy as np
import requests
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge: Advanced Sharp Analysis", layout="wide")
# Forces the app to re-run every 2 minutes to grab fresh VSiN data
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# --- 2. YOUR MODEL PROJECTIONS ---
# These are your personal percentages from your spreadsheet
my_win_projections = {
    "Angels": 35.0, "Yankees": 65.0, "Nationals": 42.0, "Rockies": 30.0,
    "Phillies": 52.0, "Rays": 45.0, "Tigers": 55.0, "Cubs": 60.0,
    "Royals": 51.0, "Marlins": 58.0, "Padres": 40.0, "D-Backs": 50.0,
    "Mariners": 58.0, "Cardinals": 48.0, "Giants": 30.0
}

# --- 3. DATA & ANALYSIS FUNCTIONS ---
@st.cache_data(ttl=110)
def fetch_live_data():
    """Fetches LIVE data from VSiN and maps it to your projections."""
    url = "https://data.vsin.com/betting-splits-data/mlb.json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        live_json = response.json().get('data', [])
        df = pd.DataFrame(live_json)
        
        # Clean numeric columns immediately so math doesn't crash
        numeric_cols = ['v_ml', 'h_ml', 'v_handle_pct', 'v_bets_pct', 'h_handle_pct', 'h_bets_pct']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        # Map VSiN names to your Projections
        def get_my_win(team_name):
            for short_name, pct in my_win_projections.items():
                if short_name.lower() in team_name.lower():
                    return pct
            return 50.0 # Default if team not found

        df['My Win% Away'] = df['away_team'].apply(get_my_win)
        df['My Win% Home'] = 100 - df['My Win% Away']
        
        # Rename columns to match your existing UI logic
        df = df.rename(columns={
            'away_team': 'Away', 
            'home_team': 'Home',
            'v_ml': 'Vegas ML Away',
            'h_ml': 'Vegas ML Home',
            'v_handle_pct': 'Handle% Away',
            'v_bets_pct': 'Bets% Away'
        })
        return df
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

def get_detailed_analysis(away, home, sharp_diff):
    """Dynamic note generator based on your spreadsheet criteria."""
    if "Angels" in away:
        return "SHARP ALERT: Detmers (LHP) faces top-10 Guardians wRC+ vs lefties. Targeting bullpen collapse."
    if "Nationals" in away:
        return "SITUATIONAL EDGE: 16mph winds out to center at GABP. Nats' 27th-ranked bullpen is the liability."
    if "Yankees" in away:
        return "VALUE PLAY: Sharps eyeing Baltimore +1.5. Bradish stabilizing. Check Ben Rice HR props (+330)."
    
    return f"MARKET FLOW: Current Sharp Diff: {int(sharp_diff)}%. Monitor Handle for late moves."

# --- 4. EXECUTION ---
df = fetch_live_data()

if not df.empty:
    # Vectorized Math (Much faster/stable than .apply)
    # Calculate Away EV
    df['Away_Payout'] = np.where(df['Vegas ML Away'] > 0, df['Vegas ML Away']/100, 100/abs(df['Vegas ML Away']))
    df['EV Away'] = (df['My Win% Away']/100 * df['Away_Payout'] * 100) - (100 - df['My Win% Away'])
    
    # Calculate Home EV
    df['Home_Payout'] = np.where(df['Vegas ML Home'] > 0, df['Vegas ML Home']/100, 100/abs(df['Vegas ML Home']))
    df['EV Home'] = (df['My Win% Home']/100 * df['Home_Payout'] * 100) - (100 - df['My Win% Home'])
    
    df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']

    # --- UI LAYOUT ---
    st.title("⚾ MLB Betting Edge: Advanced Sharp Analysis")
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    # Full Slate
    st.header("📋 Full Slate")
    st.dataframe(df[['Away', 'Home', 'Vegas ML Away', 'Vegas ML Home', 'Handle% Away', 'Bets% Away', 'EV Away', 'EV Home']], 
                 use_container_width=True, hide_index=True)

    st.divider()

    # Top Plays
    st.header("🎯 Top Plays & Sharp Moves")
    top_plays = df[(abs(df['EV Away']) > 5) | (abs(df['EV Home']) > 5) | (abs(df['Sharp Diff']) > 15)].copy()
    
    if not top_plays.empty:
        top_plays['Pick'] = np.where(top_plays['EV Away'] > top_plays['EV Home'], top_plays['Away'], top_plays['Home'])
        st.table(top_plays[['Away', 'Home', 'Pick', 'EV Away', 'EV Home', 'Sharp Diff']])
        
        st.header("📝 Sharp Scouting Reports")
        for _, row in top_plays.iterrows():
            with st.container():
                st.markdown(f"### {row['Away']} @ {row['Home']}")
                analysis_text = get_detailed_analysis(row['Away'], row['Home'], row['Sharp Diff'])
                st.info(analysis_text)
                st.markdown("---")
    else:
        st.write("Monitoring market for new Sharp movement...")
        
