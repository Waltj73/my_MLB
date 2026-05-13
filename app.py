import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG ---
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_update")

# --- 2. DATA ENGINE ---
def fetch_live_data():
    # Matches the May 13 slate from image_2e7fb4.png
    data = {
        "Away Team": ["Washington", "Colorado", "Chi Cubs", "San Diego", "SF Giants", "LA Angels", "Tampa Bay", "Kansas City", "NY Yankees", "Seattle", "Philadelphia", "Detroit", "Miami", "Arizona", "St. Louis"],
        "Home Team": ["Cincinnati", "Pittsburgh", "Atlanta", "Milwaukee", "LA Dodgers", "Cleveland", "Toronto", "Chi Sox", "Baltimore", "Houston", "Boston", "NY Mets", "Minnesota", "Texas", "Sacramento"],
        "Vegas ML Away": [139, 153, -143, 129, 199, 135, 129, -112, -173, -131, 109, -108, -126, 100, 123],
        "Vegas ML Home": [-168, -186, 119, -156, -246, -163, -156, -108, 142, 109, -131, -112, 104, -120, -149],
        "Handle% Away": [24, 37, 52, 43, 25, 37, 60, 37, 94, 64, 55, 26, 62, 47, 54],
        "Bets% Away": [34, 23, 57, 38, 25, 34, 56, 35, 91, 54, 60, 38, 35, 25, 38],
        "My Win% Away": [25.02, 18.08, 66.28, 38.25, 12.14, 21.91, 38.58, 59.24, 78.09, 71.41, 30.76, 50.00, 45.44, 43.81, 33.22],
    }
    return pd.DataFrame(data)

# --- 3. LOGIC (Matching image_2e7fb4.png exactly) ---
df = fetch_live_data()
df['My Win% Home'] = 100 - df['My Win% Away']

# Sharp ML = Handle% - Bets%
df['Sharps ML Away'] = (df['Handle% Away'] - df['Bets% Away']) / 100
df['Sharps ML Home'] = -df['Sharps ML Away']

# EV Calculation
def get_ev(win_pct, ml):
    payout = ml/100 if ml > 0 else 100/abs(ml)
    return (win_pct/100 * payout * 100) - (100 - win_pct)

df['EV Away'] = df.apply(lambda x: get_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
df['EV Home'] = df.apply(lambda x: get_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)

# Sharp Dogs Logic (Column P)
def get_sharp_dog(row):
    if row['Vegas ML Away'] > 100 and row['Sharps ML Away'] > 0.10: return row['Away Team']
    if row['Vegas ML Home'] > 100 and row['Sharps ML Home'] > 0.10: return row['Home Team']
    return ""
df['Sharp Dogs'] = df.apply(get_sharp_dog, axis=1)

# Picks Logic (Columns Y & Z)
df['Pick Away'] = df.apply(lambda x: x['Away Team'] if x['EV Away'] > 12 else "", axis=1)
df['Pick Home'] = df.apply(lambda x: x['Home Team'] if x['EV Home'] > 12 else "", axis=1)

# --- 4. UI ---
st.title("⚾ MLB Betting Edge: Sheet Sync")

# Formatting matching the spreadsheet
st.header("📋 Sync'd Full Slate")
st.dataframe(df[['Away Team', 'Home Team', 'Sharps ML Away', 'Sharps ML Home', 'Sharp Dogs', 'EV Away', 'EV Home', 'Pick Away', 'Pick Home']])

st.divider()

# Bottom Scouting Reports
st.header("📝 Sharp Scouting Reports")
top_plays = df[(df['Pick Away'] != "") | (df['Pick Home'] != "")]
for _, row in top_plays.iterrows():
    pick = row['Pick Away'] if row['Pick Away'] != "" else row['Pick Home']
    st.info(f"**{pick}**: High EV edge detected. Sharp Handle suggests institutional backing.")
