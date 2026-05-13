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

def get_detailed_tactical_notes(row):
    """Explicitly names the sharp target and model value."""
    notes = []
    sharp_val = row['Sharp_Diff']
    
    # Sharp Logic
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: Discrepancy of {sharp_val:+.0f}% favoring the Visitors.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Professional money backing the Home side ({abs(sharp_val):.0f}% diff).")
    
    # Model Logic
    if row['Away_EV'] > 0.08:
        notes.append(f"🎯 **MODEL EDGE ({row['Away']})**: Poisson projections show a +EV opportunity.")
    elif row['Home_EV'] > 0.08:
        notes.append(f"🎯 **MODEL EDGE ({row['Home']})**: Mathematical value identified on the Home side.")
        
    return notes if notes else ["Market and model are currently aligned."]

# --- 2. DATA PROCESSING ---
@st.cache_data(ttl=300)
def fetch_matchups():
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB")
        df = pd.read_html(io.StringIO(response.text), flavor='lxml')[0]
        away = df.iloc[::2].reset_index(drop=True)
        home = df.iloc[1::2].reset_index(drop=True)
        
        matchups = pd.DataFrame({
            'Away': away['MLB - Wednesday, May 13May 13.1'],
            'Home': home['MLB - Wednesday, May 13May 13.1'],
            'Away_ML': pd.to_numeric(away['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home['MoneyML'], errors='coerce'),
            'Away_Hnd': pd.to_numeric(away['HandleHND.2'].str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away['BetsBET.2'].str.extract('(\d+)')[0], errors='coerce')
        })
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups
    except: return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.title("⚾ MLB Matchup Center: Vegas vs. Poisson")

df = fetch_matchups()

if not df.empty:
    # --- POISSON MATH ---
    # Update these lambdas with your actual daily projections
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(4.5, 4.2), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    
    def ev(p, ml):
        if pd.isna(ml): return 0
        dec = (ml/100)+1 if ml > 0 else (100/abs(ml))+1
        return (p * (dec-1)) - (1-p)

    df['Away_EV'] = df.apply(lambda x: ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    # --- TABLE DISPLAY ---
    st.subheader("🏁 Full Slate Analysis")
    
    # Re-adding the missing columns from image_2ac97a.png
    display_df = df[[
        'Away', 'Home', 
        'Away_ML', 'Home_ML', 
        'Away_Win_%', 'Home_Win_%', 
        'Away_EV', 'Home_EV', 
        'Sharp_Diff'
    ]].copy()
    
    st.dataframe(
        display_df.style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}',
            'Away_EV': '{:.2%}', 'Home_EV': '{:.2%}',
            'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Home_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    # --- DETAILED SCOUTING REPORTS ---
    st.divider()
    st.subheader("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        notes = get_detailed_tactical_notes(row)
        with st.expander(f"Scouting: {row['Away']} @ {row['Home']}"):
            for n in notes: st.write(n)
            c1, c2, c3 = st.columns(3)
            c1.metric("Vegas Line", f"{row['Away_ML']}/{row['Home_ML']}")
            c2.metric("Away Poisson Win %", f"{row['Away_Win_%']:.1%}")
            
            # This directly identifies the sharp side for you
            sharp_target = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_target, f"{abs(row['Sharp_Diff'])}% Diff")
