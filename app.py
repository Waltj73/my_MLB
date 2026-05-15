import streamlit as st
import pandas as pd
import requests
import io
import sys

# Set up the Streamlit page view configuration immediately
st.set_page_config(page_title="MLB Betting Model", layout="wide")

def parse_american_odds(odds_val):
    """Safely converts betting lines (e.g. -145, +120) to implied probability fractions."""
    try:
        val_str = str(odds_val).replace('+', '').strip()
        if not val_str or any(x in val_str.lower() for x in ['vs', 'at', '@', 'nan', 'null', 'pk', 'team']):
            return 0.50
        num = float(val_str)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def run_streamlit_mlb_app():
    # Frontend Header Render Blocks
    st.title("📊 Live MLB Betting Model Dashboard")
    st.markdown("Streaming live data entries directly from your Google Sheet calculations.")
    st.divider()

    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Attempting secure data stream download
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        # Read the matrix as raw values to bypass header placement issues completely
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except Exception as e:
        st.error(f"❌ Connection Blocked by Google Sheet API: {e}")
        return

    games_list = []

    # Positional processing match loops
    for idx, row in df.iterrows():
        if len(row) < 6:
            continue
            
        away_team = str(row[0]).strip()
        home_team = str(row[1]).strip()
        
        # Sift out descriptive strings or empty spacer blocks
        if not away_team or 'nan' in away_team.lower() or 'team' in away_team.lower() or 'away' in away_team.lower():
            continue
        if not home_team or 'nan' in home_team.lower() or 'home' in home_team.lower():
            continue

        try:
            # Slicing by hard absolute columns: 0=Away, 1=Home, 2=AwayProj, 3=HomeProj, 4=VegasAway, 5=VegasHome
            away_proj = float(str(row[2]).strip())
            home_proj = float(str(row[3]).strip())
            vegas_away = row[4]
            vegas_home = row[5]
            
            total_runs = away_proj + home_proj
            if total_runs <= 0: 
                continue

            # Pure Math Execution
            model_away_p = away_proj / total_runs
            model_home_p = home_proj / total_runs
            
            vegas_away_p = parse_american_odds(vegas_away)
            vegas_home_p = parse_american_odds(vegas_home)
            
            # EV Margin outputs (Column P14 calculation matching)
            away_ev = (model_away_p - vegas_away_p) * 100
            home_ev = (model_home_p - vegas_home_p) * 100

            games_list.append({
                'away': away_team, 'home': home_team, 
                'away_proj': away_proj, 'home_proj': home_proj,
                'vegas_away': vegas_away, 'vegas_home': vegas_home,
                'model_away_p': model_away_p, 'model_home_p': model_home_p,
                'vegas_away_p': vegas_away_p, 'vegas_home_p': vegas_home_p,
                'away_ev': away_ev, 'home_ev': home_ev
            })
        except:
            continue

    if not games_list:
        st.warning("⚠ No active matchup data rows passed the numeric format filters. Check current sheet values.")
        return

    # Visualizing UI layout splits using Streamlit's dashboard columns
    col1, col2 = st.columns(2)

    with col1:
        st.header("🎯 Top Value Favorites")
        st.markdown("---")
        f_count = 0
        for g in games_list:
            if g['away_ev'] >= 4.0 and g['model_away_p'] > 0.52:
                st.subheader(f"• {g['away']} (Away) at {g['home']}")
                st.write(f"**Value Edge:** `{g['away_ev']:+.2f}% EV`")
                st.write(f"Model Probability: {g['model_away_p']:.1%} | Vegas Implied: {g['vegas_away_p']:.1%}")
                st.write(f"Projections: {g['away_proj']:.1f} runs to {g['home_proj']:.1f} runs.")
                st.divider()
                f_count += 1
            if g['home_ev'] >= 4.0 and g['model_home_p'] > 0.52:
                st.subheader(f"• {g['home']} (Home) vs. {g['away']}")
                st.write(f"**Value Edge:** `{g['home_ev']:+.2f}% EV`")
                st.write(f"Model Probability: {g['model_home_p']:.1%} | Vegas Implied: {g['vegas_home_p']:.1%}")
                st.write(f"Projections: {g['home_proj']:.1f} runs to {g['away_proj']:.1f} runs.")
                st.divider()
                f_count += 1
        if f_count == 0:
            st.info("No current matchups qualify under favorite edge targets.")

    with col2:
        st.header("🐶 Live Value Underdogs & Squads")
        st.markdown("---")
        u_count = 0
        for g in games_list:
            if g['away_ev'] >= 2.0 and g['vegas_away_p'] <= 0.51:
                st.subheader(f"• {g['away']} (Away) at {g['home']} `[Line: {g['vegas_away']}]`")
                st.write(f"**Value Edge:** `{g['away_ev']:+.2f}% EV`")
                st.write(f"Model Probability: {g['model_away_p']:.1%} | Vegas Implied: {g['vegas_away_p']:.1%}")
                st.divider()
                u_count += 1
            if g['home_ev'] >= 2.0 and g['vegas_home_p'] <= 0.51:
                st.subheader(f"• {g['home']} (Home) vs. {g['away']} `[Line: {g['vegas_home']}]`")
                st.write(f"**Value Edge:** `{g['home_ev']:+.2f}% EV`")
                st.write(f"Model Probability: {g['model_home_p']:.1%} | Vegas Implied: {g['vegas_home_p']:.1%}")
                st.divider()
                u_count += 1
        if u_count == 0:
            st.info("No plus-money selections currently hold a positive math edge.")

if __name__ == "__main__":
    run_streamlit_mlb_app()
