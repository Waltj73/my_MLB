import streamlit as st
import pandas as pd
import cloudscraper
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge: Advanced Sharp Analysis", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_update")

# --- 2. THE DATA ENGINE (Live with Fail-Safe) ---
@st.cache_data(ttl=120)
def fetch_live_data():
    """Tries to fetch live VSiN data; falls back to static if connection fails."""
    
    # 1. Start with your known working static data as the base
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

    # 2. Try to update 'Handle% Away' and 'Bets% Away' from VSiN
    try:
        scraper = cloudscraper.create_scraper()
        # VSiN raw data endpoint
        response = scraper.get("https://data.vsin.com/betting-splits-data/mlb.json", timeout=5)
        if response.status_code == 200:
            live_json = response.json().get('data', [])
            live_df = pd.DataFrame(live_json)
            
            # Map the live VSiN names to your Away/Home names to update percentages
            for i, row in df.iterrows():
                # Matching logic: Find the game in live data where away team matches
                match = live_df[live_df['away_team'].str.contains(row['Away'], case=False, na=False)]
                if not match.empty:
                    df.at[i, "Handle% Away"] = float(match.iloc[0]['v_handle_pct'])
                    df.at[i, "Bets% Away"] = float(match.iloc[0]['v_bets_pct'])
                    # Optional: Update Vegas MLs if they shifted
                    df.at[i, "Vegas ML Away"] = int(match.iloc[0]['v_ml'])
                    df.at[i, "Vegas ML Home"] = int(match.iloc[0]['h_ml'])
    except Exception as e:
        # If live fetch fails, we just keep the static 'data' from above
        pass

    df['My Win% Home'] = 100 - df['My Win% Away']
    return df

# --- 3. ANALYSIS & UI (REMAINS UNCHANGED) ---
def get_detailed_analysis(away, home, sharp_diff):
    reports = {
        ("Angels", "Guardians"): "SHARP ALERT: Massive 29% discrepancy between Handle and Bets...",
        ("Nationals", "Reds"): "SITUATIONAL EDGE: Winds are gusting 16mph straight to center...",
        ("Yankees", "Orioles"): "VALUE PLAY: Public is heavy on the NYY name, but Sharps are eyeing Baltimore...",
        ("Phillies", "Red Sox"): "MARKET CORRECTION: Handle is leaning Phillies..."
    }
    default_note = "MARKET FLOW: Current Sharp Diff: {}%. Monitor Handle for late moves.".format(sharp_diff)
    return reports.get((away, home), default_note)

df = fetch_live_data()

if not df.empty:
    # Math
    df['EV Away'] = df.apply(lambda x: (x['My Win% Away']/100 * (x['Vegas ML Away']/100 if x['Vegas ML Away']>0 else 100/abs(x['Vegas ML Away']))) - ((100-x['My Win% Away'])/100), axis=1)
    df['EV Home'] = df.apply(lambda x: (x['My Win% Home']/100 * (x['Vegas ML Home']/100 if x['Vegas ML Home']>0 else 100/abs(x['Vegas ML Home']))) - ((100-x['My Win% Home'])/100), axis=1)
    df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']

    st.title("⚾ MLB Betting Edge: Advanced Sharp Analysis")
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    st.header("📋 Full Slate")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    st.header("🎯 Top Plays & Sharp Moves")
    top_plays = df[(abs(df['EV Away']) > 0.05) | (abs(df['EV Home']) > 0.05) | (abs(df['Sharp Diff']) > 15)].copy()
    
    if not top_plays.empty:
        top_plays['Pick'] = top_plays.apply(lambda x: x['Away'] if x['EV Away'] > x['EV Home'] else x['Home'], axis=1)
        st.table(top_plays[['Away', 'Home', 'Pick', 'EV Away', 'EV Home', 'Sharp Diff']])
        
        st.header("📝 Sharp Scouting Reports")
        for _, row in top_plays.iterrows():
            with st.container():
                st.markdown(f"### {row['Away']} @ {row['Home']}")
                analysis_text = get_detailed_analysis(row['Away'], row['Home'], row['Sharp Diff'])
                st.info(analysis_text)
                st.markdown("---")
