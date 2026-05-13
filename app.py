import streamlit as st
import pandas as pd
import cloudscraper
import io

# --- 1. CORE FUNCTIONS (Defined first to prevent Line 22 errors) ---

def calculate_ev(win_prob, ml_odds):
    """Calculates EV based on your model's win % and market odds."""
    if pd.isna(ml_odds): return 0
    # Convert American Odds to Decimal
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    # EV = (Prob * Profit) - (Loss Prob * Stake)
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

def get_pick_details(row):
    """Generates detailed scouting notes for the tactical dashboard."""
    notes = []
    # Sharp Logic: Handle significantly higher than Bets
    if row['Sharp_Diff'] > 15:
        notes.append(f"🐳 **SHARP MOVE**: Pro money is flooding this side ({row['Sharp_Diff']:.1f}% diff).")
    
    # EV Logic: Model Win % vs Market Implied
    if row['EV'] > 0.05:
        notes.append(f"🎯 **VALUE**: Your model shows a {row['Edge']:.1f}% edge over the book.")
    
    # Combined "Best Bet" Logic
    if row['EV'] > 0 and row['Sharp_Diff'] > 10:
        notes.append("🔥 **TACTICAL PLAY**: Model value aligns with Sharp flow.")
        
    return " | ".join(notes) if notes else "Market and model are currently in sync."

@st.cache_data(ttl=300)
def fetch_vsin_splits():
    """Scrapes live betting splits."""
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data, flavor='lxml')
        for df in tables:
            # Match the headers found in your screencapture-my-mlb-streamlit-app-2026-05-13-10_52_17.png
            if any(term in str(df.columns) for term in ['Matchup', 'Handle', 'HND']):
                return df
        return tables[0]
    except Exception as e:
        st.error(f"Data Fetch Error: {str(e)[:100]}")
        return pd.DataFrame()

# --- 2. MAIN EXECUTION ---

st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Tactical Dashboard: EV & Sharp Flow")

df = fetch_vsin_splits()

if not df.empty:
    # Column Mappings from screencapture-my-mlb-streamlit-app-2026-05-13-10_52_17.png
    team_col = 'MLB - Wednesday, May 13May 13.1'
    ml_col = 'MoneyML'
    handle_col = 'HandleHND.2' # Away Moneyline Handle
    bets_col = 'BetsBET.2'     # Away Moneyline Bets

    # Data Cleaning
    df['Odds'] = pd.to_numeric(df[ml_col], errors='coerce')
    df['Handle_Pct'] = df[handle_col].astype(str).str.extract('(\d+)').astype(float)
    df['Bets_Pct'] = df[bets_col].astype(str).str.extract('(\d+)').astype(float)
    df['Sharp_Diff'] = df['Handle_Pct'] - df['Bets_Pct']
    
    # 3. INTEGRATE YOUR MODEL
    # Replace 0.52 with your actual daily win probability variable/script output
    df['My_Win_Prob'] = 0.52 
    
    # 4. MATH CALCULATIONS
    df['EV'] = df.apply(lambda x: calculate_ev(x['My_Win_Prob'], x['Odds']), axis=1)
    df['Implied_Prob'] = df['Odds'].apply(lambda x: 100/(x+100) if x > 0 else abs(x)/(abs(x)+100))
    df['Edge'] = (df['My_Win_Prob'] * 100) - df['Implied_Prob']

    # 5. UI DISPLAY
    st.subheader("📊 Full Slate & Value Analysis")
    
    # Filtering columns for the main view
    view_df = df[[team_col, ml_col, 'My_Win_Prob', 'EV', 'Edge', 'Sharp_Diff']].copy()
    
    # Apply Styling (Ensure matplotlib is in requirements.txt)
    st.dataframe(
        view_df.style.background_gradient(subset=['EV', 'Edge', 'Sharp_Diff'], cmap='RdYlGn'),
        hide_index=True, 
        use_container_width=True
    )

    st.divider()
    
    # 6. DETAILED PICK NOTES
    st.subheader("🧠 Tactical Scouting Reports")
    
    # Filter for games where there is an edge or sharp interest
    picks = df[(df['EV'] > 0) | (abs(df['Sharp_Diff']) > 10)]
    
    if not picks.empty:
        for _, row in picks.iterrows():
            with st.expander(f"Analysis: {row[team_col]} ({row[ml_col]})"):
                st.write(get_pick_details(row))
                col1, col2 = st.columns(2)
                col1.metric("Model EV", f"{row['EV']:.2%}")
                col2.metric("Sharp Differential", f"{row['Sharp_Diff']:+.1f}%")
    else:
        st.write("Monitoring market... no high-conviction plays currently detected.")
