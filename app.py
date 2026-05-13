import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Exact Replicator) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    """Calculates win probability using the Poisson distribution (0-15 range)."""
    if not away_lambda or not home_lambda or away_lambda == 0:
        return 0.50 
    
    scores = np.arange(16) # Range used in your Excel LET formula
    
    # Exact score probabilities
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    # Cumulative probabilities (scoring k-1 or fewer)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    # Win probability logic (SUMPRODUCT style)
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    """Calculates Expected Value based on Win % and Vegas Moneyline."""
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. DETAILED TACTICAL NOTES ---
def get_detailed_tactical_notes(row):
    """Generates scouting notes naming teams and sharp direction."""
    notes = []
    sharp_val = row['Sharp_Diff']
    
    # Sharp Logic: Positive = Away side, Negative = Home side
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: Discrepancy of {sharp_val:+.0f}% favoring the Visitors.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Professional money is backing the Home side ({abs(sharp_val):.0f}% diff).")
    
    # Model Logic based on Poisson EV
    if row['Away_EV'] > 0.08:
        notes.append(f"🎯 **MODEL VALUE ({row['Away']})**: Poisson edge identified against Vegas odds.")
    elif row['Home_EV'] > 0.08:
        notes.append(f"🎯 **MODEL VALUE ({row['Home']})**: Mathematical value identified on the Home side.")
        
    return notes if notes else ["Market and model are currently aligned."]

# --- 3. DATA ACQUISITION (TARGETING EST SCORE) ---
@st.cache_data(ttl=300)
def fetch_matchup_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        # Identify the correct betting splits table
        df = None
        for table in tables:
            if 'EST Score' in table.columns or 'ESTScore' in table.columns:
                df = table
                break
        
        if df is None: 
            # Fallback if VSiN changes header name again
            for table in tables:
                if any('team' in str(c).lower() for c in table.columns):
                    df = table
                    break
        
        if df is None: return pd.DataFrame()

        # Split into Away and Home pairings
        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, 1], # Team Name
            'Home': home_rows.iloc[:, 1],
            'Away_ML': pd.to_numeric(away_rows['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows['MoneyML'], errors='coerce'),
            # TARGETING EST SCORE FOR POISSON LAMBDAS
            'Away_Proj': pd.to_numeric(away_rows['EST Score'], errors='coerce').fillna(4.5),
            'Home_Proj': pd.to_numeric(home_rows['EST Score'], errors='coerce').fillna(4.2),
            'Away_Hnd': pd.to_numeric(away_rows['HandleHND.2'].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows['BetsBET.2'].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away', 'Home'])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---
st.set_page_config(page_title="MLB Poisson Dashboard", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_matchup_data()

if not df.empty:
    # Execute Math with EST Scores
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis (Poisson vs. Vegas)")
    
    # Final Table View
    view_cols = ['Away', 'Home', 'Away_ML', 'Home_ML', 'Away_Win_%', 'Home_Win_%', 'Away_EV', 'Home_EV', 'Sharp_Diff']
    st.dataframe(
        df[view_cols].style.format({
            'Away_Win_%': '{:.1%}', 'Home_Win_%': '{:.1%}',
            'Away_EV': '{:.2%}', 'Home_EV': '{:.2%}',
            'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['Away_EV', 'Home_EV', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, use_container_width=True
    )

    st.divider()
    st.header("🧠 Tactical Scouting Reports")
    for _, row in df.iterrows():
        notes = get_detailed_tactical_notes(row)
        with st.expander(f"Scouting Report: {row['Away']} @ {row['Home']}"):
            for n in notes: st.write(n)
            c1, c2, c3 = st.columns(3)
            c1.metric("Away Poisson Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
            # Identifies the specific team the sharps are backing
            sharp_target = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_target, f"{abs(row['Sharp_Diff'])}% Diff")
else:
    st.info("Searching for EST Scores and latest betting splits...")
