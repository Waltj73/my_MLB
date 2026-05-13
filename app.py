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

# --- 2. THE BRUTE-FORCE SCRAPER ---
@st.cache_data(ttl=300)
def fetch_vsin_brute_force():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url, timeout=10)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        target_df = None
        for df in tables:
            # FLATTEN MULTI-INDEX HEADERS: This is likely where it was breaking.
            # It turns [('Un-named', 'Team'), ('DraftKings', 'MoneyML')] into 'Team MoneyML'
            df.columns = [" ".join(str(level) for level in col).strip() if isinstance(col, tuple) else str(col) for col in df.columns]
            
            # Look for the table that actually has the data
            col_txt = " ".join(df.columns).lower()
            if 'ml' in col_txt or 'money' in col_txt:
                target_df = df
                break
        
        if target_df is None: return pd.DataFrame()

        # Helper to find column by "contains" logic
        def find_col(keywords):
            for col in target_df.columns:
                if any(k.lower() in col.lower() for k in keywords): return col
            return None

        col_team = find_col(['team', 'matchup'])
        col_ml = find_col(['money', 'ml'])
        col_est = find_col(['est', 'score'])
        col_hnd = find_col(['hnd', 'handle'])
        col_bets = find_col(['bet', 'count'])

        # Unstack rows (Away/Home)
        away = target_df.iloc[::2].reset_index(drop=True)
        home = target_df.iloc[1::2].reset_index(drop=True)

        final = pd.DataFrame({
            'Away': away[col_team],
            'Home': home[col_team],
            'Away_ML': pd.to_numeric(away[col_ml], errors='coerce'),
            'Away_Proj': pd.to_numeric(away[col_est], errors='coerce'),
            'Home_Proj': pd.to_numeric(home[col_est], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away[col_hnd].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away[col_bets].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        final['Sharp_Diff'] = final['Away_Hnd'] - final['Away_Bets']
        return final.dropna(subset=['Away', 'Away_Proj'])

    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 3. UI ---
st.set_page_config(page_title="MLB Tactical Fix", layout="wide")
st.title("⚾ MLB Automated Tactical Dashboard")

df = fetch_vsin_brute_force()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)

    st.header("🏁 Live Slate Analysis")
    st.dataframe(
        df.style.format({
            'Away_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )
else:
    st.warning("⚠️ Still no data. VSiN might be blocking the request or the headers are deeper than expected.")
