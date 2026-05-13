import streamlit as st
import pandas as pd
import cloudscraper
import io

# --- 1. CORE FUNCTIONS ---

def calculate_ev(win_prob, ml_odds):
    if pd.isna(ml_odds): return 0
    decimal_odds = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (decimal_odds - 1)) - (1 - win_prob)

@st.cache_data(ttl=300)
def fetch_vsin_splits():
    url = "https://data.vsin.com/betting-splits/?source=DK&sport=MLB"
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        html_data = io.StringIO(response.text)
        tables = pd.read_html(html_data, flavor='lxml')
        for df in tables:
            # Targeted mapping from screencapture-my-mlb-streamlit-app-2026-05-13-10_57_19.jpg
            if any(term in str(df.columns) for term in ['Matchup', 'Handle', 'HND']):
                return df
        return tables[0]
    except Exception as e:
        st.error(f"Data Fetch Error: {str(e)[:100]}")
        return pd.DataFrame()

# --- 2. DATA PROCESSING ---

st.set_page_config(page_title="MLB Tactical Dashboard", layout="wide")
st.title("⚾ MLB Tactical Dashboard: EV & Sharp Flow")

df = fetch_vsin_splits()

if not df.empty:
    # Column Mappings as seen in screencapture-my-mlb-streamlit-app-2026-05-13-10_57_19.jpg
    team_col = 'MLB - Wednesday, May 13May 13.1'
    vegas_line_col = 'MoneyML'
    handle_col = 'HandleHND.2'
    bets_col = 'BetsBET.2'

    # Cleaning & Conversions
    df['Vegas Line'] = pd.to_numeric(df[vegas_line_col], errors='coerce')
    df['Handle_Pct'] = df[handle_col].astype(str).str.extract('(\d+)').astype(float)
    df['Bets_Pct'] = df[bets_col].astype(str).str.extract('(\d+)').astype(float)
    df['Sharp_Diff'] = df['Handle_Pct'] - df['Bets_Pct']
    
    # 3. MODEL INTEGRATION (Using your established 52% placeholder)
    df['My_Win_Prob'] = 0.52 
    
    # 4. MATH CALCULATIONS
    df['EV'] = df.apply(lambda x: calculate_ev(x['My_Win_Prob'], x['Vegas Line']), axis=1)
    df['Implied_Prob'] = df['Vegas Line'].apply(lambda x: 100/(x+100) if x > 0 else abs(x)/(abs(x)+100))
    df['Edge'] = (df['My_Win_Prob'] * 100) - df['Implied_Prob']

    # --- 5. NEW: TODAY'S TOP TACTICAL PICKS ---
    # High conviction = Positive EV AND Sharp interest
    top_picks = df[(df['EV'] > 0) & (df['Sharp_Diff'] > 5)].sort_values(by='EV', ascending=False)

    st.header("🔥 Today's Top Tactical Picks")
    if not top_picks.empty:
        # Displaying only the most important columns for the "Picks" table
        pick_display = top_picks[[team_col, 'Vegas Line', 'EV', 'Sharp_Diff']].copy()
        st.dataframe(
            pick_display.style.format({
                'EV': '{:.2%}',
                'Sharp_Diff': '{:+.0f}%'
            }).background_gradient(subset=['EV'], cmap='Greens'),
            hide_index=True, use_container_width=True
        )
    else:
        st.write("Searching for high-conviction value... check back closer to first pitch.")

    st.divider()

    # --- 6. FULL SLATE ANALYSIS (WITH PERCENTAGE FORMATTING) ---
    st.header("📊 Full Slate & Value Analysis")
    
    # We rename columns here for the UI to be cleaner
    view_df = df[[team_col, 'Vegas Line', 'My_Win_Prob', 'EV', 'Edge', 'Sharp_Diff']].copy()
    view_df.columns = ['Team', 'Vegas Line', 'Model Win %', 'EV', 'Edge %', 'Sharp Diff']
    
    # Apply precise percentage formatting to resolve the long decimal issue
    st.dataframe(
        view_df.style.format({
            'Model Win %': '{:.0%}',
            'EV': '{:.2%}',
            'Edge %': '{:+.1f}%',
            'Sharp Diff': '{:+.0f}%'
        }).background_gradient(subset=['EV', 'Edge %', 'Sharp Diff'], cmap='RdYlGn'),
        hide_index=True, 
        use_container_width=True
    )
