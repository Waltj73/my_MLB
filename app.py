import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Fixed Unpacking) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Calculates win probability using the Poisson distribution (0-15 range)."""
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0:
        return 0.50 
    
    scores = np.arange(16) 
    # FIXED: Separate calls for away and home PMFs
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. DATA ACQUISITION (Targeting EST Score from image.png) ---
@st.cache_data(ttl=300)
def fetch_matchup_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        df = None
        for table in tables:
            # Look for the Moneyline and EST columns specifically
            if 'MoneyML' in table.columns or 'EST Score' in table.columns:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # Handle the stacked Away/Home structure from your screenshot
        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, 1],
            'Home': home_rows.iloc[:, 1],
            'Away_ML': pd.to_numeric(away_rows['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows['MoneyML'], errors='coerce'),
            'Away_Proj': pd.to_numeric(away_rows['EST Score'], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_rows['EST Score'], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away_rows['HandleHND.2'].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows['BetsBET.2'].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away', 'Home', 'Away_Proj'])
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Poisson Dashboard", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_matchup_data()

if not df.empty:
    # Calculations
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    view_cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Home_EV', 'Sharp_Diff']
    st.dataframe(
        df[view_cols].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}',
            'Away_EV': '{:.2%}', 'Home_EV': '{:.2%}',
            'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Home_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(row['Sharp_Diff']):.0f}% discrepancy).")
            st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) vs {row['Home']} ({row['Home_Proj']})")
            
            c1, c2 = st.columns(2)
            c1.metric("Away Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
else:
    st.info("Awaiting live data from VSiN...")
