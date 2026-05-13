import streamlit as st
import pandas as pd
import numpy as np  # Required for the fix
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP ---
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_update")

# --- 2. DATA (Matches image_2e7fb4.png) ---
def fetch_live_data():
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

df = fetch_live_data()
df['My Win% Home'] = 100 - df['My Win% Away']

# --- 3. THE FIX: VECTORIZED MATH ---
# Calculate Payout (Decimal Odds) using np.where to avoid the ValueError
df['Away Payout'] = np.where(df['Vegas ML Away'] > 0, df['Vegas ML Away']/100, 100/abs(df['Vegas ML Away']))
df['Home Payout'] = np.where(df['Vegas ML Home'] > 0, df['Vegas ML Home']/100, 100/abs(df['Vegas ML Home']))

# Calculate Implied Win%
df['Vegas Win% Away'] = 100 / (df['Away Payout'] + 1)
df['Vegas Win% Home'] = 100 / (df['Home Payout'] + 1)

# Sharps ML (Column H & N)
df['Sharps ML Away'] = (df['Handle% Away'] - df['Bets% Away']) / 100
df['Sharps ML Home'] = -df['Sharps ML Away']

# Differences (Column U & V)
df['Diff Away'] = df['My Win% Away'] - df['Vegas Win% Away']
df['Diff Home'] = df['My Win% Home'] - df['Vegas Win% Home']

# EV (Column V & W in sheet)
df['EV Away'] = (df['My Win% Away']/100 * df['Away Payout'] * 100) - (100 - df['My Win% Away'])
df['EV Home'] = (df['My Win% Home']/100 * df['Home Payout'] * 100) - (100 - df['My Win% Home'])

# Picks (Column Y & Z)
df['Pick Away'] = np.where(df['EV Away'] > 12, df['Away Team'], "")
df['Pick Home'] = np.where(df['EV Home'] > 12, df['Home Team'], "")

# --- 4. STYLING & UI ---
st.title("⚾ MLB Betting Dashboard")

def highlight_cols(x):
    style_df = pd.DataFrame('', index=x.index, columns=x.columns)
    for col in ['EV Away', 'EV Home', 'Diff Away', 'Diff Home']:
        style_df[col] = x[col].apply(lambda v: 'background-color: #2ecc71; color: black' if v > 10 else ('background-color: #f1948a; color: black' if v < -10 else ''))
    for col in ['Pick Away', 'Pick Home']:
        style_df[col] = x[col].apply(lambda v: 'background-color: #16a085; color: white; font-weight: bold' if v != "" else '')
    return style_df

st.dataframe(
    df[['Away Team', 'Home Team', 'Sharps ML Away', 'Sharps ML Home', 'EV Away', 'EV Home', 'Diff Away', 'Diff Home', 'Pick Away', 'Pick Home']]
    .style.apply(highlight_cols, axis=None),
    use_container_width=True,
    height=600,
    hide_index=True
)
