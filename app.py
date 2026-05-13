import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if not away_lambda or not home_lambda: return 0.50
    scores = np.arange(16)
    away_pmf, home_pmf = poisson.pmf(scores, away_lambda), poisson.pmf(scores, home_lambda)
    away_cdf, home_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda), poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    prob_away = np.sum(away_pmf * home_cdf)
    prob_home = np.sum(home_pmf * away_cdf)
    return prob_away / (prob_away + prob_home)

def get_tactical_notes(row):
    """Rebuilds notes based on Matchup data."""
    notes = []
    if abs(row['Sharp_Diff']) > 15:
        side = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
        notes.append(f"🐳 **Sharp Alert**: Significant pro flow on {side}.")
    if abs(row['EV']) > 0.08:
        side = row['Away'] if row['EV'] > 0 else row['Home']
        notes.append(f"🎯 **Model Edge**: High Poisson EV on {side}.")
    return " | ".join(notes) if notes else "Market aligned with model."

# --- 2. DATA PROCESSING ---
@st.cache_data(ttl=300)
def fetch_and_pivot_matchups():
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB")
        df = pd.read_html(io.StringIO(response.text), flavor='lxml')[0]
        
        # VSiN lists Away Team then Home Team in consecutive rows
        # We split them and merge them side-by-side
        away_df = df.iloc[::2].reset_index(drop=True)
        home_df = df.iloc[1::2].reset_index(drop=True)
        
        matchups = pd.DataFrame({
            'Away': away_df['MLB - Wednesday, May 13May 13.1'],
            'Home': home_df['MLB - Wednesday, May 13May 13.1'],
            'Away_ML': pd.to_numeric(away_df['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home_df['MoneyML'], errors='coerce'),
            'Away_Sharp': pd.to_numeric(away_df['HandleHND.2'].str.extract('(\d+)')[0], errors='coerce') - 
                         pd.to_numeric(away_df['BetsBET.2'].str.extract('(\d+)')[0], errors='coerce')
        })
        return matchups
    except: return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.set_page_config(page_title="MLB Poisson Matchups", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_and_pivot_matchups()

if not df.empty:
    # Poisson Inputs (Placeholders for your run projections)
    df['Away_Exp'] = 4.5
    df['Home_Exp'] = 4.2
    
    # Calculate Probabilities
    df['Away_Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Exp'], x['Home_Exp']), axis=1)
    df['Home_Win_Prob'] = 1 - df['Away_Win_Prob']
    
    # Calculate EV (Focusing on Away side for the table logic)
    def calc_ev(prob, ml):
        if pd.isna(ml): return 0
        dec = (ml/100)+1 if ml > 0 else (100/abs(ml))+1
        return (prob * (dec-1)) - (1-prob)

    df['EV'] = df.apply(lambda x: calc_ev(x['Away_Win_Prob'], x['Away_ML']), axis=1)
    df['Sharp_Diff'] = df['Away_Sharp'] # Comparing Away sharp movement
    
    # --- DISPLAY ---
    st.header("🏁 Game Slate: Away vs Home")
    
    # Clean display table
    view_cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_Prob', 'Home_Win_Prob', 'EV', 'Sharp_Diff']
    formatted_df = df[view_cols].copy()
    
    st.dataframe(
        formatted_df.style.format({
            'Away_Win_Prob': '{:.1%}', 'Home_Win_Prob': '{:.1%}',
            'EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    
    # --- SCOUTING NOTES ---
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        note = get_tactical_notes(row)
        with st.expander(f"Matchup: {row['Away']} @ {row['Home']}"):
            st.write(note)
            c1, c2 = st.columns(2)
            c1.metric(f"{row['Away']} Win %", f"{row['Away_Win_Prob']:.1%}")
            c2.metric("Away EV", f"{row['EV']:.2%}")
