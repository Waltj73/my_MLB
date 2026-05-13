import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP ---
st.set_page_config(page_title="MLB Betting Edge", layout="wide")
st_autorefresh(interval=60 * 1000, key="vsin_update")

# --- 2. DATA (Hard-coded to match your image_2e7fb4.png exactly) ---
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

# --- 3. THE "WALT JOHNSON" ENGINE ---
df = fetch_live_data()
df['My Win% Home'] = 100 - df['My Win% Away']

# Sharps ML Logic (Column H & N)
df['Sharps ML Away'] = (df['Handle% Away'] - df['Bets% Away']) / 100
df['Sharps ML Home'] = -df['Sharps ML Away']

# EV Logic (Column V & W)
def calc_ev(win_pct, ml):
    payout = ml/100 if ml > 0 else 100/abs(ml)
    return (win_pct/100 * payout * 100) - (100 - win_pct)

df['EV Away'] = df.apply(lambda x: calc_ev(x['My Win% Away'], x['Vegas ML Away']), axis=1)
df['EV Home'] = df.apply(lambda x: calc_ev(x['My Win% Home'], x['Vegas ML Home']), axis=1)

# Difference Logic (Column U & V)
df['Diff Away'] = df['My Win% Away'] - (100 / ( (df['Vegas ML Away']/100 if df['Vegas ML Away']>0 else 100/abs(df['Vegas ML Away'])) + 1))
df['Diff Home'] = df['My Win% Home'] - (100 / ( (df['Vegas ML Home']/100 if df['Vegas ML Home']>0 else 100/abs(df['Vegas ML Home'])) + 1))

# Picks (Column Y & Z)
df['Pick Away'] = df.apply(lambda x: x['Away Team'] if x['EV Away'] > 12 else "", axis=1)
df['Pick Home'] = df.apply(lambda x: x['Home Team'] if x['EV Home'] > 12 else "", axis=1)

# --- 4. STYLING (The "Sheet Look") ---
def highlight_cols(x):
    # Match the green/red shading from image_2e7fb4.png
    style_df = pd.DataFrame('', index=x.index, columns=x.columns)
    
    # EV & Diff Highlighting
    for col in ['EV Away', 'EV Home', 'Diff Away', 'Diff Home']:
        style_df[col] = x[col].apply(lambda v: 'background-color: #2ecc71' if v > 10 else ('background-color: #f1948a' if v < -10 else ''))
    
    # Picks Column Highlighting
    for col in ['Pick Away', 'Pick Home']:
        style_df[col] = x[col].apply(lambda v: 'background-color: #16a085; color: white; font-weight: bold' if v != "" else '')
        
    return style_df

# --- 5. THE OUTPUT ---
st.title("⚾ MLB Betting Dashboard")

# Display as one massive, styled spreadsheet
st.dataframe(
    df[['Away Team', 'Home Team', 'Sharps ML Away', 'Sharps ML Home', 'EV Away', 'EV Home', 'Diff Away', 'Diff Home', 'Pick Away', 'Pick Home']]
    .style.apply(highlight_cols, axis=None),
    use_container_width=True,
    height=600,
    hide_index=True
)

st.divider()

# Only keep the notes in a very small section at the bottom
st.subheader("📝 Quick Sharp Notes")
sharp_dogs = df[((df['Vegas ML Away'] > 100) & (df['Sharps ML Away'] > 0.10)) | ((df['Vegas ML Home'] > 100) & (df['Sharps ML Home'] > 0.10))]
for _, row in sharp_dogs.iterrows():
    dog = row['Away Team'] if row['Vegas ML Away'] > 0 else row['Home Team']
    st.caption(f"**Sharp Dog Alert:** {dog} showing institutional support vs. market price.")
