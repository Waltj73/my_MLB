import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
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

# --- 2. FUZZY TEAM MATCHING LOGIC ---
def clean_team_name(name):
    """Standardizes names to improve matching (e.g., 'NY Mets' -> 'METS')"""
    name = str(name).upper().strip()
    # Remove city names or common variations if needed
    return name.split()[-1] # Return just the mascot name for better matching

# --- 3. DUAL-SOURCE SCRAPER ---
@st.cache_data(ttl=300)
def fetch_and_merge_data():
    scraper = cloudscraper.create_scraper()
    try:
        # PULL GAMES (EST Scores)
        res1 = scraper.get("https://data.vsin.com/mlb/games/", timeout=10)
        df_games = pd.read_html(io.StringIO(res1.text), flavor='lxml')[0]
        
        # PULL SPLITS (Handle/Bets)
        res2 = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB", timeout=10)
        df_splits = pd.read_html(io.StringIO(res2.text), flavor='lxml')[0]

        def get_idx(df, keywords):
            for i, col in enumerate(df.columns):
                if any(k in str(col).lower() for k in keywords): return i
            return 1

        # Process Games
        idx_est = get_idx(df_games, ['est'])
        idx_ml = get_idx(df_games, ['money', 'ml'])
        
        away_g = df_games.iloc[::2].reset_index(drop=True)
        home_g = df_games.iloc[1::2].reset_index(drop=True)
        
        games = pd.DataFrame({
            'Away': away_g.iloc[:, 1],
            'Home': home_g.iloc[:, 1],
            'Away_Proj': pd.to_numeric(away_g.iloc[:, idx_est], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_g.iloc[:, idx_est], errors='coerce'),
            'Away_ML': pd.to_numeric(away_g.iloc[:, idx_ml], errors='coerce'),
            'Match_Key': away_g.iloc[:, 1].apply(clean_team_name)
        })

        # Process Splits
        idx_hnd = get_idx(df_splits, ['hnd', 'handle'])
        idx_bets = get_idx(df_splits, ['bet', 'count'])
        
        away_s = df_splits.iloc[::2].reset_index(drop=True)
        splits = pd.DataFrame({
            'Split_Key': away_s.iloc[:, 1].apply(clean_team_name),
            'Handle': pd.to_numeric(away_s.iloc[:, idx_hnd].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Bets': pd.to_numeric(away_s.iloc[:, idx_bets].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })

        # Join and Clean
        final = pd.merge(games, splits, left_on='Match_Key', right_on='Split_Key', how='left')
        final['Sharp_Diff'] = final['Handle'] - final['Bets']
        return final.dropna(subset=['Away', 'Away_Proj'])

    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 4. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Automated Tactical Dashboard")

df = fetch_and_merge_data()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Live Slate Analysis")
    view_cols = ['Away', 'Home', 'Away_ML', 'Away_Proj', 'Home_Proj', 'Away_Win_%', 'Away_EV', 'Sharp_Diff']
    st.dataframe(
        df[view_cols].style.format({
            'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            sharp_team = row['Away'] if (row['Sharp_Diff'] or 0) > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(row['Sharp_Diff'] or 0):.0f}% discrepancy).")
            st.write(f"📊 **EST Scores**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
            st.metric("Away Poisson Win %", f"{row['Away_Win_%']:.1%}")
else:
    st.info("🔄 Running Final Team Sync... This will fix the '0' team values seen in image_2067d9.png.")
