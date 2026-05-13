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

# --- 2. THE REINFORCED SYNC ENGINE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1240994733'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_live_slate():
    try:
        # Load raw without headers first
        raw_df = pd.read_csv(URL, header=None).fillna('')
        
        # FIXED: Deep-Scan with float protection
        header_row_index = 0
        for i, row in raw_df.iterrows():
            # Force everything to string before checking 'away' or 'home'
            row_str_list = [str(val).lower() for val in row.tolist()]
            if any("away" in s for s in row_str_list) and any("home" in s for s in row_str_list):
                header_row_index = i
                break
        
        # Re-load from the identified header row
        df = pd.read_csv(URL, skiprows=header_row_index)
        df.columns = [str(c).strip().replace('"', '') for c in df.columns]
        return df.dropna(subset=[df.columns[0]])
    except Exception as e:
        st.error(f"Sync Interrupted: {e}")
        return pd.DataFrame()

# --- 3. UI & TACTICAL ANALYSIS ---
st.set_page_config(page_title="MLB Tactical Command", layout="wide")
st.title("⚾ MLB Tactical Command Center")

df = load_live_slate()

if not df.empty:
    def find_col(keywords):
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords): return col
        return None

    # Mapping your specific columns
    c_away = find_col(['Away'])
    c_home = find_col(['Home'])
    c_a_est = find_col(['Away EST', 'A_EST'])
    c_h_est = find_col(['Home EST', 'H_EST'])
    c_ml = find_col(['MoneyML', 'ML'])
    c_hnd = find_col(['HandleHND.2', 'Handle', 'HND'])
    c_bet = find_col(['BetsBET.2', 'Bets', 'BET'])

    if not c_away or not c_home:
        st.error("Header Scan failed to find 'Away' or 'Home' columns.")
        st.stop()

    def clean_num(val):
        return pd.to_numeric(str(val).replace('%','').strip(), errors='coerce')

    # Data Processing
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
    # Focusing on EV and Implied Win % over estimated runs
    m1.metric("Model Win %", f"{g['Win_Prob']:.1%}")
    m2.metric("Edge (EV)", f"{g['EV']:.2%}")
    m3.metric("Sharp Discrepancy", f"{g['Sharp_Diff']:.0f}%")

    st.divider()
    
    l, r = st.columns(2)
    with l:
        st.subheader("🎯 Tactical Notes")
        st.write(f"Projections: **{g.get(c_a_est)}** vs **{g.get(c_h_est)}**")
        if g['EV'] > 0.08: st.success("**Value Alert**: High EV detected.")
        elif g['EV'] < -0.08: st.warning("**Overvalued**: Market price exceeds model.")

    with r:
        st.subheader("🐳 Institutional Flow")
        if abs(g['Sharp_Diff']) > 15:
            st.info(f"**Sharp Move**: {g['Sharp_Diff']:.0f}% money-to-ticket gap.")
        else:
            st.write("Market sentiment is balanced.")

    st.caption("🔄 Data synced live from Google Sheet tab [MLB]. Refresh every 30s.")
else:
    st.info("🔄 Connecting... Ensure the MLB tab contains your Away/Home headers.")
