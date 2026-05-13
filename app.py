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
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. THE TACTICAL NOTES ---
def get_detailed_tactical_notes(row):
    notes = []
    sharp_val = row['Sharp_Diff']
    if sharp_val > 10:
        notes.append(f"🐳 **SHARPS ON {row['Away'].upper()}**: Discrepancy of {sharp_val:+.0f}% favoring the Visitors.")
    elif sharp_val < -10:
        notes.append(f"🏠 **SHARPS ON {row['Home'].upper()}**: Professional money backing the Home side ({abs(sharp_val):.0f}% diff).")
    if row['Away_EV'] > 0.08:
        notes.append(f"🎯 **MODEL VALUE ({row['Away']})**: Poisson edge identified.")
    elif row['Home_EV'] > 0.08:
        notes.append(f"🎯 **MODEL VALUE ({row['Home']})**: Mathematical edge on the Home side.")
    return notes if notes else ["Market and model are currently aligned."]

# --- 3. THE RELIABLE DATA ACQUISITION ---
@st.cache_data(ttl=300)
def fetch_matchup_data():
    scraper = cloudscraper.create_scraper()
    try:
        url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        
        # Find the table that contains actual team data
        df = None
        for table in tables:
            if any('team' in str(c).lower() or 'mlb' in str(c).lower() for c in table.columns):
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # Split into Away and Home rows
        away_rows = df.iloc[::2].reset_index(drop=True)
        home_rows = df.iloc[1::2].reset_index(drop=True)

        # Mapping columns by their EXACT names as they appear on the VSiN site
        # We use .filter or string matching to ensure we don't grab 'Total' or 'Spread'
        matchups = pd.DataFrame({
            'Away': away_rows.iloc[:, 1], # Team Name
            'Home': home_rows.iloc[:, 1],
            'Away_ML': pd.to_numeric(away_rows['MoneyML'], errors='coerce'),
            'Home_ML': pd.to_numeric(home_rows['MoneyML'], errors='coerce'),
            'Away_Proj': pd.to_numeric(away_rows['ProjectedScore'], errors='coerce').fillna(4.5),
            'Home_Proj': pd.to_numeric(home_rows['ProjectedScore'], errors='coerce').fillna(4.2),
            'Away_Hnd': pd.to_numeric(away_rows['HandleHND.2'].astype(str).str.extract('(\d+)')[0], errors='coerce'),
            'Away_Bets': pd.to_numeric(away_rows['BetsBET.2'].astype(str).str.extract('(\d+)')[0], errors='coerce')
        })
        
        matchups['Sharp_Diff'] = matchups['Away_Hnd'] - matchups['Away_Bets']
        return matchups.dropna(subset=['Away', 'Home'])
    except Exception as e:
        st.error(f"Error fetching VSiN data: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---
st.set_page_config(page_title="MLB Poisson Dashboard", layout="wide")
st.title("⚾ MLB Matchup Tactical Dashboard")

df = fetch_matchup_data()

if not df.empty:
    # Run the Math
    df['Away_Win_%'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Proj'], x['Home_Proj']), axis=1)
    df['Home_Win_%'] = 1 - df['Away_Win_%']
    df['Away_EV'] = df.apply(lambda x: calculate_ev(x['Away_Win_%'], x['Away_ML']), axis=1)
    df['Home_EV'] = df.apply(lambda x: calculate_ev(x['Home_Win_%'], x['Home_ML']), axis=1)

    st.header("🏁 Full Slate Analysis")
    
    # Selection and Display
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
            c1.metric("Away Win %", f"{row['Away_Win_%']:.1%}")
            c2.metric("Away EV", f"{row['Away_EV']:.2%}")
            sharp_target = row['Away'] if row['Sharp_Diff'] > 0 else row['Home']
            c3.metric("Sharp Target", sharp_target, f"{abs(row['Sharp_Diff'])}% Diff")
