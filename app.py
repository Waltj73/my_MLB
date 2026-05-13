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
    """Generates explicit notes on Sharp direction and Model Value."""
    notes = []
    
    # SHARP ANALYSIS
    sharp_val = row['Sharp_Diff']
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: Big money discrepancy ({sharp_val:+.0f}%) favoring the Visitors.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Professional money is backing the Home side ({abs(sharp_val):.0f}% diff).")
    
    # MODEL VALUE ANALYSIS
    if row['Away_EV'] > 0.10:
        notes.append(f"💰 **MODEL VALUE ({row['Away']})**: Poisson projections show massive +EV at {row['Away_ML']} odds.")
    elif row['Home_EV'] > 0.10:
        notes.append(f"💰 **MODEL VALUE ({row['Home']})**: Mathematical edge on the Home side according to Poisson.")

    # TRAP DETECTION
    if row['Away_EV'] > 0.05 and sharp_val < -15:
        notes.append(f"⚠️ **TRAP ALERT**: Model likes {row['Away']}, but Sharps are hammering {row['Home']}. Proceed with caution.")
        
    return notes if notes else ["Market and model are currently in equilibrium."]

# --- 2. DATA PROCESSING ---
@st.cache_data(ttl=300)
def fetch_matchups():
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get("https://data.vsin.com/betting-splits/?source=DK&sport=MLB")
        df = pd.read_html(io.StringIO(response.text), flavor='lxml')[0]
        
        # Merge rows into Matchups
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
st.title("⚾ MLB Tactical Matchup Center")

df = fetch_matchups()

if not df.empty:
    # Poisson Setup (Using your spreadsheet's lambda logic)
    df['Away_Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(4.5, 4.2), axis=1) # Replace with real lambdas
    df['Home_Win_Prob'] = 1 - df['Away_Win_Prob']
    
    # EV Calculations for both sides
    def ev(p, ml):
        if pd.isna(ml): return 0
        dec = (ml/100)+1 if ml > 0 else (100/abs(ml))+1
        return (p * (dec-1)) - (1-p)

    df['Away_EV'] = df.apply(lambda x: ev(x['Away_Win_Prob'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: ev(x['Home_Win_Prob'], x['Home_ML']), axis=1)

    # MASTER TABLE
    st.subheader("🏁 Full Slate Analysis")
    # Custom display to show "Sharp Side" explicitly
    view = df[['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_EV', 'Home_EV', 'Sharp_Diff']].copy()
    
    st.dataframe(
        view.style.format({
            'Away_EV': '{:.2%}', 'Home_EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Home_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    # DETAILED SCOUTING REPORTS
    st.divider()
    st.subheader("🧠 Tactical Scouting Reports")
    
    for _, row in df.iterrows():
        notes = get_detailed_tactical_notes(row)
        with st.expander(f"Scouting: {row['Away']} @ {row['Home']}"):
            for n in notes:
                st.write(n)
            
            # Clarity Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Away EV", f"{row['Away_EV']:.1%}")
            c2.metric("Home EV", f"{row['Home_EV']:.1%}")
            
            # This directly answers "Who are the sharps on?"
            sharp_team = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_team, f"{abs(row['Sharp_Diff'])}% Diff")
