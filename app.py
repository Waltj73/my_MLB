import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & REFRESH ---
st.set_page_config(page_title="MLB Betting Edge + Analysis", layout="wide")
st_autorefresh(interval=2 * 60 * 1000, key="vsin_analysis_update")

# --- 2. DATA & WRITE-UP ENGINE ---
def get_analysis(away, home):
    """
    Function to provide a short write-up based on current market trends.
    In a production version, this would fetch from an RSS feed or API.
    """
    writeups = {
        ("Angels", "Guardians"): "Sharps are fading Detmers due to a bottom-tier Angels bullpen (5.45 ERA). Cleveland ML is the play.",
        ("Yankees", "Orioles"): "Ben Rice is the HR target here; his 203 wRC+ against RHP matches up perfectly against Bradish.",
        ("Nationals", "Reds"): "High winds (16mph out) at Great American Ball Park favor the Reds' power hitters against a weak Nats pen.",
        ("Phillies", "Red Sox"): "Market correction spot. Public is heavy on Boston, but the Sharp Handle is leaning toward the Phillies' pitching depth."
    }
    return writeups.get((away, home), "Market analysis pending: Watch for late-breaking Sharp movement on the Handle.")

@st.cache_data(ttl=120)
def fetch_live_data():
    # Simulated Slate for May 13
    data = {
        "Away": ["Angels", "Yankees", "Nationals", "Rockies", "Phillies"],
        "Home": ["Guardians", "Orioles", "Reds", "Pirates", "Red Sox"],
        "Vegas ML Away": [135, -173, 139, 153, 109],
        "Vegas ML Home": [-163, 142, -168, -186, -131],
        "Handle% Away": [5, 99, 21, 8, 29],
        "Bets% Away": [34, 91, 57, 23, 60],
        "My Win% Away": [35.0, 65.0, 42.0, 30.0, 52.0],
    }
    df = pd.DataFrame(data)
    df['My Win% Home'] = 100 - df['My Win% Away']
    return df

# --- 3. CALCS & UI ---
df = fetch_live_data()

# Replicating your sheet's EV logic
def calculate_ev(win_pct, ml):
    payout = ml / 100 if ml > 0 else 100 / abs(ml)
    return ((win_pct / 100) * payout) - ((100 - win_pct) / 100)

if not df.empty:
    df['EV Away'] = df.apply(lambda x: calculate_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
    df['EV Home'] = df.apply(lambda x: calculate_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)
    df['Sharp Diff'] = df['Handle% Away'] - df['Bets% Away']
    
    # Add the write-up column
    df['Analysis'] = df.apply(lambda x: get_analysis(x['Away'], x['Home']), axis=1)

    st.title("⚾ MLB Edge Dashboard + Expert Write-ups")

    # --- TOP PLAYS HIGHLIGHTED ---
    st.header("🎯 Today's Top Picks & Analysis")
    
    # Thresholds: EV > 5% or Sharp Diff > 15
    top_plays = df[(df['EV Away'] > 0.05) | (df['EV Home'] > 0.05) | (abs(df['Sharp Diff']) > 15)].copy()
    
    if not top_plays.empty:
        for index, row in top_plays.iterrows():
            with st.expander(f"🔥 {row['Away']} @ {row['Home']} - Click for Scouting Report"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("Sharp Diff", f"{row['Sharp Diff']}%")
                    side = row['Away'] if row['EV Away'] > row['EV Home'] else row['Home']
                    st.write(f"**Recommended Side:** {side}")
                with col2:
                    st.write("**Expert Analysis:**")
                    st.info(row['Analysis'])
    
    st.divider()
    
    # --- FULL SLATE ---
    st.header("📋 Full Slate")
    st.dataframe(df.drop(columns=['Analysis']), use_container_width=True, hide_index=True)
