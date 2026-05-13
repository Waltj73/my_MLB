import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Exact Excel Replicator) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Replicates your SUMPRODUCT Poisson formula in Python."""
    if not away_lambda or not home_lambda or away_lambda == 0:
        return 0.50 # Default to coin flip if data is missing
    
    # 0-15 run range as defined in your Excel LET formula
    scores = np.arange(16)
    
    # Probabilities of exact scores (POISSON.DIST(..., FALSE))
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    # Cumulative probs for k-1 (POISSON.DIST(..., TRUE))
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    # Win probability calculation
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. DETAILED TACTICAL NOTES ---
def get_detailed_tactical_notes(row):
    """Provides explicit team-based scouting reports."""
    notes = []
    sharp_val = row['Sharp_Diff']
    
    # Sharp Logic: Positive = Away, Negative = Home
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: Big money discrepancy ({sharp_val:+.0f}%) favoring the Visitors.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Professional money is backing the Home side ({abs(sharp_val):.0f}% diff).")
    
    # Model Logic
    if row['Away_EV'] > 0.10:
        notes.append(f"🎯 **MODEL VALUE ({row['Away']})**: Poisson model identifies significant edge at current odds.")
    elif row['Home_EV'] > 0.10:
        notes.append(f"🎯 **MODEL VALUE ({row['Home']})**: Mathematical edge on the Home side according to Poisson.")

    # Trap Detection
    if row['Away_EV'] > 0.05 and sharp_val < -15:
        notes.append(f"⚠️ **TRAP ALERT**: Model likes {row['Away']}, but Sharps are hammering {row['Home']}.")
        
    return notes if notes else ["Market and model are currently in equilibrium."]

# --- 3. ROBUST DATA ACQUISITION ---
@st.cache_data(ttl=300)
def fetch_matchup_data():
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB")
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        # Fuzzy search for the correct betting splits table
        target_df = None
        for table in tables:
            if 'hnd' in " ".join(table.columns.astype(str)).lower():
                target_df = table
                break
        
        if target_df is None: return pd.DataFrame()

        # Group rows into Matchups (Away/Home)
        away = target_df.iloc[::2].reset_index(drop=True)
        home = target_df.iloc[1::2].reset_index(drop=True)
        
        # Build the structured dataframe using position-based indexing (iloc)
        matchups = pd.DataFrame({
            'Away': away.iloc[:, 1],
            'Home': home.iloc[:, 1],
            'Away_ML': pd.to_numeric(away.iloc[:, 5], errors='coerce'),
            'Home_ML': pd.to_numeric(home.iloc[:, 5], errors='coerce'),
            'Away_Proj': pd.to_numeric(away.filter(like='Proj').iloc[:, 0], errors='coerce').fillna(4.5),
            'Home_Proj': pd.to_numeric(home.filter(like='Proj').iloc[:, 0], errors='coerce').fillna(4.2),
            'Away_Hnd': pd.to_numeric(away.iloc[:, 9].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away.iloc[:, 10].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---
st.set_page_config(page_title="MLB Poisson Matchup Center", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_matchup_data()

if not df.empty:
    # RUN CALCULATIONS
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    # MASTER TABLE
    st.header("🏁 Full Slate Analysis")
    view = df[['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Home_EV', 'Sharp_Diff']].copy()
    
    st.dataframe(
        view.style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}',
            'Away_EV': '{:.2%}', 'Home_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Home_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    # TACTICAL SCOUTING REPORTS
    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        notes = get_detailed_tactical_notes(row)
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            for note in notes:
                st.write(note)
            
            # Conviction Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Away Win Prob", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
            
            # Explicit Sharp Target Identification
            sharp_target = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_target, f"{abs(row['Sharp_Diff'])}% Diff")
else:
    st.info("Loading latest betting splits and Poisson projections...")
