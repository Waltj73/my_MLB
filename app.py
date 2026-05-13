import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Exact Replicator) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Calculates win probability using the Poisson distribution (0-15 range)."""
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0:
        return 0.50 
    
    scores = np.arange(16) # Range from your Excel LET formula
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

# --- 2. DETAILED TACTICAL NOTES ---
def get_detailed_tactical_notes(row):
    notes = []
    sharp_val = row['Sharp_Diff']
    
    # Sharp Identification: Positive = Away, Negative = Home
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: {sharp_val:+.0f}% money discrepancy.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Pros backing the Home side ({abs(sharp_val):.0f}% diff).")
    
    # Model Value Notes
    if row['Away_EV'] > 0.08:
        notes.append(f"🎯 **MODEL EDGE ({row['Away']})**: Poisson math identifies value.")
    elif row['Home_EV'] > 0.08:
        notes.append(f"🎯 **MODEL EDGE ({row['Home']})**: Value identified on Home side.")
        
    return notes if notes else ["Market and model are currently aligned."]

# --- 3. RESILIENT DATA ACQUISITION ---
@st.cache_data(ttl=300)
def fetch_vsin_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        df = None
        for table in tables:
            col_txt = " ".join(table.columns.astype(str)).lower()
            if 'hnd' in col_txt or 'handle' in col_txt:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # FUZZY COLUMN LOCATOR: Finds 'EST Score', 'MoneyML', etc.
        def find_idx(keywords):
            for i, col in enumerate(df.columns):
                if any(k.lower() in str(col).lower() for k in keywords): return i
            return None

        idx_team = find_idx(['team', 'mlb', 'matchup']) or 1
        idx_ml = find_idx(['money', 'ml']) or 5
        idx_est = find_idx(['est score', 'estscore', 'proj']) or 7
        idx_hnd = find_idx(['hnd', 'handle']) or 9
        idx_bets = find_idx(['bet', 'count']) or 10

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
        return matchups.dropna(subset=['Away', 'Home', 'Away_Proj'])
    except Exception as e:
        st.error(f"Fuzzy Search Error: {e}")
        return pd.DataFrame()

# --- 4. UI DASHBOARD ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Tactical Matchup Center")

df = fetch_vsin_data()

if not df.empty:
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    view = df[['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Sharp_Diff']]
    st.dataframe(view.style.format({
        'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}', 'Away_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
    }).background_gradient(subset=['Away_EV', 'Sharp_Diff'], cmap='RdYlGn'), hide_index=True, use_container_width=True)

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        notes = get_detailed_tactical_notes(row)
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            for n in notes: st.write(n)
            c1, c2, c3 = st.columns(3)
            c1.metric("Poisson Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_team, f"{abs(row['Sharp_Diff'])}% Diff")
else:
    st.info("Searching for EST Scores and Moneyline splits...")
