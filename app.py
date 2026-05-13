import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Your Precise Excel Math) ---
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

# --- 2. THE AGGRESSIVE SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url, timeout=10)
        # We read all tables and search for the one with 'EST' or 'Score'
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        main_df = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any('est' in c or 'score' in c for c in cols):
                main_df = t
                break
        
        if main_df is None: return pd.DataFrame()

        # Step 3: Unstacking the 'EST Score' and 'MoneyML' rows
        # VSiN lists Away on Row 0, Home on Row 1 for every game
        away_rows = main_df.iloc[::2].reset_index(drop=True)
        home_rows = main_df.iloc[1::2].reset_index(drop=True)

        # Dynamic mapping based on column keywords
        def find_col(keywords):
            for i, col in enumerate(main_df.columns):
                if any(k.lower() in str(col).lower() for k in keywords): return i
            return None

        idx_est = find_col(['est', 'score'])
        idx_ml = find_col(['money', 'ml'])
        idx_team = find_col(['team', 'matchup'])

        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, idx_team],
            'Home': home_rows.iloc[:, idx_team],
            'Away_Proj': pd.to_numeric(away_rows.iloc[:, idx_est], errors='coerce'),
            'Home_Proj': pd.to_numeric(home_rows.iloc[:, idx_est], errors='coerce'),
            'Away_ML': pd.to_numeric(away_rows.iloc[:, idx_ml], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows.iloc[:, idx_ml], errors='coerce')
        })
        return matchups.dropna(subset=['Away_Proj'])
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return pd.DataFrame()

# --- 3. UI DISPLAY ---
st.set_page_config(page_title="MLB Automation", layout="wide")
st.title("⚾ MLB Automated Tactical Center")

df = fetch_vsin_data()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    
    st.header("📊 Live Data & Poisson Projections")
    st.dataframe(df.style.format({
        'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}'
    }), hide_index=True, use_container_width=True)

    st.divider()
    st.header("🧠 Tactical Notes")
    for _, row in df.iterrows():
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            st.write(f"📊 **EST Scores Scraped**: {row['Away']} ({row['Away_Proj']}) | {row['Home']} ({row['Home_Proj']})")
            st.write(f"🎯 **Win Probability**: {row['Away']} has a {row['Away_Win_%']:.1%} chance to win based on Poisson engine.")
else:
    st.warning("🔄 Connecting to VSiN... If this stays blank, the 'EST Score' column name might have changed slightly on the live site.")
