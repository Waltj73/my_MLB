import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# --- 1. CORE MATH ENGINE ---
def calculate_poisson_win_prob(away_lambda, home_lambda):
    if pd.isna(away_lambda) or pd.isna(home_lambda) or away_lambda <= 0 or home_lambda <= 0:
        return 0.50
    scores = np.arange(16)
    away_pmf, home_pmf = poisson.pmf(scores, away_lambda), poisson.pmf(scores, home_lambda)
    away_cdf, home_cdf = poisson.cdf(np.maximum(0, scores - 1), away_lambda), poisson.cdf(np.maximum(0, scores - 1), home_lambda)
    p_away = np.sum(away_pmf * home_cdf)
    p_home = np.sum(home_pmf * away_cdf)
    return p_away / (p_away + p_home)

def calculate_ev(win_prob, ml_odds):
    if not ml_odds or pd.isna(ml_odds): return 0
    dec = (ml_odds / 100) + 1 if ml_odds > 0 else (100 / abs(ml_odds)) + 1
    return (win_prob * (dec - 1)) - (1 - win_prob)

# --- 2. THE HARDENED SYNC ENGINE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_live_slate():
    try:
        # Load the whole sheet raw to find where the data actually starts
        raw_df = pd.read_csv(URL, header=None).fillna('')
        
        # Step A: Find the header row by looking for "Away" or "Home" anywhere in the row
        header_row_index = 0
        found = False
        for i, row in raw_df.iterrows():
            # Clean each cell: convert to string, lower case, remove non-alphanumeric
            row_vals = [str(x).lower().strip() for x in row.values]
            if any("away" in val for val in row_vals) and any("home" in val for val in row_vals):
                header_row_index = i
                found = True
                break
        
        if not found:
            # Fallback: If no headers found, just try to use the first row and hope for the best
            header_row_index = 0

        # Step B: Reload from that specific row
        df = pd.read_csv(URL, skiprows=header_row_index)
        # Clean column names strictly: remove special characters, extra spaces, and quotes
        df.columns = [str(c).strip().replace('"', '').replace('\n', '') for c in df.columns]
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Sync Interrupted: {e}")
        return pd.DataFrame()

# --- 3. UI & TACTICAL ANALYSIS ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_live_slate()

if not df.empty:
    def find_col(keywords):
        # Fuzzy match to handle "Away EST", "A_EST", "AwayEST", etc.
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords):
                return col
        return None

    # Mapping your specific MLB columns
    c_away = find_col(['away'])
    c_home = find_col(['home'])
    c_a_est = find_col(['away est', 'a_est', 'a est'])
    c_h_est = find_col(['home est', 'h_est', 'h est'])
    c_ml = find_col(['moneyml', 'ml', 'money ml'])
    c_hnd = find_col(['handlehnd.2', 'handle', 'hnd'])
    c_bet = find_col(['betsbet.2', 'bets', 'bet'])

    # Final Guardrail
    if not c_away or not c_home:
        st.warning("⚠️ Column detection is struggling. Showing available columns below:")
        st.write(list(df.columns))
        st.stop()

    def clean_num(val):
        # Strips % and commas, handles spaces, converts to float
        s = str(val).replace('%', '').replace(',', '').strip()
        return pd.to_numeric(s, errors='coerce')

    # Data Processing with your logic for EV and implied win probabilities
    df['Win_Prob'] = df.apply(lambda x: calculate_poisson_win_prob(clean_num(x.get(c_a_est, 0)), clean_num(x.get(c_h_est, 0))), axis=1)
    df['EV'] = df.apply(lambda x: calculate_ev(x['Win_Prob'], clean_num(x.get(c_ml, 0))), axis=1)
    df['Sharp_Diff'] = clean_num(df.get(c_hnd, 0)) - clean_num(df.get(c_bet, 0))

    # Matchup Selection
    game_list = (df[c_away].astype(str) + " @ " + df[c_home].astype(str)).tolist()
    selected_game = st.selectbox("🎯 Select Matchup", game_list)
    g = df[(df[c_away].astype(str) + " @ " + df[c_home].astype(str)) == selected_game].iloc[0]

    # --- TACTICAL SCOUTING REPORT ---
    st.header(f"📈 Scouting Report: {g[c_away]} @ {g[c_home]}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
    m2.metric("Edge (EV)", f"{g['EV']:.2%}")
    m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

    st.divider()
    
    l, r = st.columns(2)
    with l:
        st.subheader("🎯 Tactical Notes")
        # Direct reference to your EST Score lambdas
        st.write(f"Projections: **{g.get(c_a_est)}** vs **{g.get(c_h_est)}**")
        if g['EV'] > 0.08: st.success("**Value Alert**: High EV detected.")
        elif g['EV'] < -0.08: st.warning("**Overvalued**: Market price exceeds model.")

    with r:
        st.subheader("🐳 Institutional Flow")
        # Focus on "Sharp Action" discrepancies
        if abs(g['Sharp_Diff']) > 15:
            st.info(f"**Sharp Move**: {g['Sharp_Diff']:.0f}% money-to-ticket gap.")
        else:
            st.write("Market sentiment is balanced.")

    st.caption("🔄 Data synced live from Google Sheet tab [MLB]. Refresh every 30s.")
else:
    st.info("🔄 Connecting... Please ensure the 'MLB' tab in your sheet isn't empty.")
