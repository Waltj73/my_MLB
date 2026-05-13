import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import cloudscraper
import io

# --- 1. THE POISSON ENGINE (Replicating your Excel LET formula) ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if not away_lambda or not home_lambda or away_lambda == 0:
        return 0.50 # Default to coin flip if data is missing
    
    scores = np.arange(16) # 0 to 15 runs
    
    # Probabilities of exact scores (POISSON.DIST(..., FALSE))
    away_pmf = poisson.pmf(scores, away_lambda)
    home_pmf = poisson.pmf(scores, home_lambda)
    
    # Probabilities of scoring k-1 or fewer (POISSON.DIST(..., TRUE))
    away_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda)
    home_cdf = poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    
    # SUMPRODUCT logic for win probabilities
    prob_away_wins = np.sum(away_pmf * home_cdf)
    prob_home_wins = np.sum(home_pmf * away_cdf)
    
    # Return normalized win % (away_prob / (away_prob + home_prob))
    return prob_away_wins / (prob_away_wins + prob_home_wins)

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

# --- 2. DATA ACQUISITION ---
@st.cache_data(ttl=300)
def fetch_data():
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        tables = pd.read_html(io.StringIO(response.text), flavor='lxml')
        for df in tables:
            if 'Matchup' in str(df.columns) or 'HND' in str(df.columns):
                return df
        return tables[0]
    except Exception:
        return pd.DataFrame()

# --- 3. DASHBOARD EXECUTION ---
st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Poisson Tactical Dashboard")

df = fetch_data()

if not df.empty:
    # Mapping based on screencapture-my-mlb-streamlit-app-2026-05-13-11_00_32.png
    team_col = 'MLB - Wednesday, May 13May 13.1'
    vegas_col = 'MoneyML'
    handle_col = 'HandleHND.2'
    bets_col = 'BetsBET.2'

    # Cleaning
    df['Vegas Odds'] = pd.to_numeric(df[vegas_col], errors='coerce')
    df['Handle_Pct'] = df[handle_col].astype(str).str.extract('(\d+)').astype(float)
    df['Bets_Pct'] = df[bets_col].astype(str).str.extract('(\d+)').astype(float)
    df['Sharp_Diff'] = df['Handle_Pct'] - df['Bets_Pct']

    # --- 4. POISSON INTEGRATION ---
    # Here we simulate your 'away_lambda' and 'home_lambda' (Expected Runs)
    # In your production version, you'd pull these from your MLB stats database.
    df['Away_Exp_Runs'] = 4.5 # Placeholder
    df['Home_Exp_Runs'] = 4.2 # Placeholder
    
    df['My Win %'] = df.apply(lambda x: calculate_poisson_win_prob(x['Away_Exp_Runs'], x['Home_Exp_Runs']), axis=1)
    df['EV'] = df.apply(lambda x: calculate_ev(x['My Win %'], x['Vegas Odds']), axis=1)

    # --- 5. UI DISPLAY ---
    st.header("🎯 Today's High-Value Tactical Picks")
    # Filters for picks: Positive EV + Positive Sharp Movement
    picks = df[(df['EV'] > 0.05) & (df['Sharp_Diff'] > 5)].copy()
    
    if not picks.empty:
        st.dataframe(picks[[team_col, 'Vegas Odds', 'My Win %', 'EV', 'Sharp_Diff']].style.format({
            'My Win %': '{:.1%}', 'EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
        }).background_gradient(subset=['EV'], cmap='Greens'), hide_index=True, use_container_width=True)
    else:
        st.write("No high-conviction plays currently meet the Poisson + Sharp criteria.")

    st.divider()
    st.header("📊 Full Slate Analysis")
    st.dataframe(df[[team_col, 'Vegas Odds', 'My Win %', 'EV', 'Sharp_Diff']].style.format({
        'My Win %': '{:.1%}', 'EV': '{:.2%}', 'Sharp_Diff': '{:+.0f}%'
    }).background_gradient(subset=['EV', 'Sharp_Diff'], cmap='RdYlGn'), hide_index=True, use_container_width=True)
