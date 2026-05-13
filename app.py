import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if not away_lambda or not home_lambda or away_lambda == 0:
        return 0.50 
    scores = np.arange(16)
    away_pmf, home_pmf = poisson.pmf(scores, away_lambda)
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

# --- 2. THE RESILIENT SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        # FIND THE TABLE: Look for "HND" or "Handle" anywhere in the table
        df = None
        for table in tables:
            col_txt = " ".join(table.columns.astype(str)).lower()
            if 'hnd' in col_txt or 'handle' in col_txt:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # DYNAMIC COLUMN FINDER: Prevents blank screen if names change
        def find_idx(keywords):
            for i, col in enumerate(df.columns):
                if any(k.lower() in str(col).lower() for k in keywords):
                    return i
            return None

        # Map indices based on the keywords found in your screenshots
        idx_team = find_idx(['team', 'mlb', 'matchup']) or 1
        idx_ml = find_idx(['money', 'ml']) or 5
        idx_est = find_idx(['est score', 'estscore', 'proj']) or 7
        idx_hnd = find_idx(['hnd', 'handle']) or 9
        idx_bets = find_idx(['bet', 'count']) or 10

        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, idx_team],
            'Home': home_rows.iloc[:, idx_team],
            'Away_ML': pd.to_numeric(away_rows.iloc[:, idx_ml], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows.iloc[:, idx_ml], errors='coerce'),
            'Away_Proj': pd.to_numeric(away_rows.iloc[:, idx_est], errors='coerce').fillna(4.5),
            'Home_Proj': pd.to_numeric(home_rows.iloc[:, idx_est], errors='coerce').fillna(4.2),
            'Away_Hnd': pd.to_numeric(away_rows.iloc[:, idx_hnd].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows.iloc[:, idx_bets].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away', 'Home'])
        
    except Exception as e:
        st.error(f"⚠️ App Encountered an Error: {e}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Tactical Matchup Center")

df = fetch_vsin_data()

if not df.empty:
    # RUN CALCULATIONS
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    # Display table mirroring your manual spreadsheet
    view_cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Sharp_Diff']
    st.dataframe(
        df[view_cols].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            # Detailed notes explaining sharp direction
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            st.write(f"🐳 **Sharp Target**: {sharp_team} ({abs(row['Sharp_Diff']):.0f}% discrepancy between money and bets).")
            
            if abs(row['Away_EV']) > 0.10:
                side = row['Away'] if row['Away_EV'] > 0 else row['Home']
                st.write(f"🎯 **Model Edge**: Poisson projections show high value on {side}.")
            
            c1, c2 = st.columns(2)
            c1.metric(f"{row['Away']} Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
else:
    st.info("Searching for the latest MLB data and EST Scores...")
