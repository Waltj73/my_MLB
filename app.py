import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Calculates win probability using the Poisson distribution (0-15 range)."""
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0:
        return 0.50 
    
    scores = np.arange(16)
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. THE RESILIENT SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url, timeout=10)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        df = None
        for table in tables:
            # Flatten columns to lowercase strings to find the right table
            col_txt = " ".join(table.columns.astype(str)).lower()
            if 'hnd' in col_txt or 'handle' in col_txt:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # DYNAMIC COLUMN LOCATOR: Finds the index of a column by searching for keywords
        def get_col_idx(keywords):
            for i, col in enumerate(df.columns):
                if any(k.lower() in str(col).lower() for k in keywords):
                    return i
            return None

        # Map indices using your specific naming conventions
        idx_team = get_col_idx(['matchup', 'mlb', 'team']) or 1
        idx_ml = get_col_idx(['money', 'ml']) or 5
        idx_est = get_col_idx(['est score', 'estscore']) or 7 # TARGETING YOUR "EST Score"
        idx_hnd = get_col_idx(['hnd', 'handle']) or 9
        idx_bets = get_col_idx(['bet', 'count']) or 10

        # Split into Away (Even) and Home (Odd) rows
        away = df.iloc[::2].reset_index(drop=True)
        home = df.iloc[1::2].reset_index(drop=True)

        matchups = pd.DataFrame({
            'Away': away.iloc[:, idx_team],
            'Home': home.iloc[:, idx_team],
            'Away_ML': pd.to_numeric(away.iloc[:, idx_ml], errors='coerce'),
            'Home_ML': pd.to_numeric(home.iloc[:, idx_ml], errors='coerce'),
            'Away_Proj': pd.to_numeric(away.iloc[:, idx_est], errors='coerce'),
            'Home_Proj': pd.to_numeric(home.iloc[:, idx_est], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away.iloc[:, idx_hnd].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away.iloc[:, idx_bets].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away', 'Away_Proj'])
    except Exception as e:
        st.error(f"Logic Error: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_vsin_data()

if not df.empty:
    # RUN POISSON MATH
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    # TABLE DISPLAY (Mirrors your manual spreadsheet)
    st.header("🏁 Full Slate Analysis")
    cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Sharp_Diff']
    st.dataframe(
        df[cols].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            # SHARP TARGET IDENTIFICATION BY NAME
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(row['Sharp_Diff']):.0f}% discrepancy).")
            st.write(f"📊 **EST Scores Used**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
            
            c1, c2 = st.columns(2)
            c1.metric(f"{row['Away']} Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
else:
    st.warning("⚠️ Data Sync Issue: The dashboard is looking for the 'EST Score' column. Please refresh in a moment.")
