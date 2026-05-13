import streamlit as st
import pandas as pd
import cloudscraper
import io

# --- 1. CORE MATH ENGINE ---
def calculate_ev(win_prob, ml_odds):
    """Calculates EV based on your model's win % and market odds."""
    # Convert American Odds to Decimal for the formula
    if ml_odds > 0:
        decimal_odds = (ml_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(ml_odds)) + 1
    
    # EV Formula: (Probability * Profit) - (Loss Probability * Stake)
    ev = (win_prob * (decimal_odds - 1)) - (1 - win_prob)
    return ev * 100 # Return as percentage

# --- 2. DATA SOURCE ---
@st.cache_data(ttl=300)
def fetch_vsin_splits():
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data, flavor='lxml')
        for df in tables:
            if any(term in str(df.columns) for term in ['Matchup', 'Handle', 'Bets', 'HND']):
                return df
        return tables[0]
    except Exception as e:
        st.error(f"Scraper Error: {str(e)[:100]}")
        return pd.DataFrame()

# --- 3. UI DASHBOARD ---
st.title("⚾ MLB Tactical Dashboard: EV & Sharp Flow")

df = fetch_vsin_splits()

if not df.empty:
    # Based on screencapture-my-mlb-streamlit-app-2026-05-13-10_52_17.png headers
    team_col = 'MLB - Wednesday, May 13May 13.1'
    ml_col = 'MoneyML'
    handle_col = 'HandleHND.2'
    bets_col = 'BetsBET.2'

    # Clean the Data
    df['Odds'] = pd.to_numeric(df[ml_col], errors='coerce')
    df['Handle_Val'] = df[handle_col].astype(str).str.extract('(\d+)').astype(float)
    df['Bets_Val'] = df[bets_col].astype(str).str.extract('(\d+)').astype(float)
    
    # Calculate Implied Prob from Market
    df['Implied_Prob'] = df['Odds'].apply(lambda x: 100/(x+100) if x > 0 else abs(x)/(abs(x)+100))

    # --- 4. YOUR MODEL INPUTS ---
    # In a full setup, you would import your Python script's results here.
    # For now, we use a placeholder for your win % logic.
    st.sidebar.header("Model Inputs")
    st.sidebar.info("Integrating Python script win probabilities...")
    
    # Placeholder: In your final version, this is where your CSV or Script output maps to teams
    # For this demo, let's assume a flat 52% model win rate to test the logic
    df['My_Win_Prob'] = 0.52 

    # --- 5. THE MASTER TABLE ---
    df['EV'] = df.apply(lambda x: calculate_ev(x['My_Win_Prob'], x['Odds']), axis=1)
    df['Sharp_Diff'] = df['Handle_Val'] - df['Bets_Val']
    df['Edge'] = (df['My_Win_Prob'] * 100) - (df['Implied_Prob'] * 100)

    # Styling for the "Pick" column
    def identify_pick(row):
        if row['EV'] > 5 and row['Sharp_Diff'] > 10: return "🔥 STRONG BUY"
        if row['EV'] > 0: return "✅ VALUE PLAY"
        return "❌ NO BET"

    df['Action'] = df.apply(identify_pick, axis=1)

    st.subheader("Full Slate & EV Analysis")
    display_cols = [team_col, ml_col, 'My_Win_Prob', 'EV', 'Edge', 'Sharp_Diff', 'Action']
    st.dataframe(df[display_cols].style.background_gradient(subset=['EV', 'Sharp_Diff'], cmap='RdYlGn'), 
                 hide_index=True, use_container_width=True)

    # --- 6. SHARP ANALYSIS SECTION ---
    st.divider()
    st.subheader("🎯 Sharp Money Alerts")
    sharps = df[abs(df['Sharp_Diff']) > 15]
    if not sharps.empty:
        cols = st.columns(len(sharps))
        for i, (idx, row) in enumerate(sharps.iterrows()):
            with cols[i]:
                st.metric(row[team_col], f"{row['Sharp_Diff']:+.1f}%", delta="Sharp Divergence")
    else:
        st.write("No extreme sharp divergences detected.")
