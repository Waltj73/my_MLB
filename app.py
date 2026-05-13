import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Core Math) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0:
        return 0.50 
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    p_away = np.sum(away_pmf * home_cdf)
    p_home = np.sum(home_pmf * away_cdf)
    return p_away / (p_away + p_home)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. RESTORED SCRAPER (Split Page Focused) ---
@st.cache_data(ttl=300)
def fetch_vsin_baseline():
    scraper = cloudscraper.create_scraper()
    try:
        # Focusing on the Betting Splits page as the primary table
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url, timeout=10)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        # We look for the main betting table (usually table 0 or 1)
        df = None
        for t in tables:
            if 'money' in "".join(t.columns.astype(str)).lower():
                df = t
                break
        
        if df is None: return pd.DataFrame()

        # UNSTACKING LOGIC: Away (even rows), Home (odd rows)
        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        # MAPPING: Specifically targeting column names from image_2067d9.png
        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, 1],
            'Home': home_rows.iloc[:, 1],
            'Away_ML': pd.to_numeric(away_rows['MoneyML'], errors='coerce'),
            'Away_Proj': pd.to_numeric(away_rows['EST Score'], errors='coerce'), # Pulled from Splits Page column
            'Home_Proj': pd.to_numeric(home_rows['EST Score'], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away_rows['HandleHND.2'].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows['BetsBET.2'].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away_Proj'])

    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. DASHBOARD DISPLAY ---
st.set_page_config(page_title="MLB Restored Baseline", layout="wide")
st.title("⚾ MLB Tactical Matchup Center")

df = fetch_vsin_baseline()

if not df.empty:
    # Calculations
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Live Slate Analysis")
    cols = ['Away', 'Home', 'Away_ML', 'Away_Proj', 'Home_Proj', 'Away_Win_%', 'Away_EV', 'Sharp_Diff']
    st.dataframe(df[cols].style.format({
        'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
    }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'), 
    hide_index=True, use_container_width=True)

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
            st.metric("Away Poisson Win %", f"{row['Away_Win_%']:.1%}")
else:
    st.info("🔄 Connecting to VSiN Splits Table...")
