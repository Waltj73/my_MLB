import pandas as pd
import requests
import io
import sys

def parse_american_odds(odds_val):
    """Safely converts betting lines (e.g. -145, +120) to implied probability."""
    try:
        val_str = str(odds_val).replace('+', '').strip()
        if not val_str or any(x in val_str.lower() for x in ['vs', 'at', '@', 'nan', 'null', 'pk']):
            return 0.50
        num = float(val_str)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def run_mlb_live_sheet_model():
    # Production link configuration targeting the matchups tab
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    # Browser headers to prevent Google from blocking or hanging the script
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("🔄 Connecting directly to Google Sheet API stream...")
    try:
        # Fetch with an explicit 10-second timeout so it cannot freeze on a blank screen
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Read the raw downloaded text data directly into memory
        raw_df = pd.read_csv(io.StringIO(response.text))
    except requests.exceptions.Timeout:
        print("\n❌ CONNECTION TIMEOUT: Google took too long to respond. Try running the script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ACCESS DENIED: Unable to stream URL data. Error: {e}")
        print("💡 Quick Fix: Ensure your Google Sheet sharing is set to 'Anyone with the link can view'.")
        sys.exit(1)
        
    # Standardize column labels to drop whitespace/case variations
    raw_df.columns = raw_df.columns.str.strip().str.lower()
    
    # Map column structures dynamically based on positional index fallbacks
    col_map = {}
    required_keys = ['away_team', 'home_team', 'away_proj', 'home_proj', 'away_odds', 'home_odds']
    indices_fallback = [0, 1, 2, 3, 4, 5]
    
    # Scan columns for exact context match
    for col in raw_df.columns:
        if 'away' in col or 'team 1' in col:
            if 'proj' in col or 'run' in col: col_map['away_proj'] = col
            elif 'line' in col or 'odds' in col or 'vegas' in col: col_map['away_odds'] = col
            else: col_map['away_team'] = col
        elif 'home' in col or 'team 2' in col:
            if 'proj' in col or 'run' in col: col_map['home_proj'] = col
            elif 'line' in col or 'odds' in col or 'vegas' in col: col_map['home_odds'] = col
            else: col_map['home_team'] = col

    # Bind indices if keyword tracking did not find a 100% match
    for key, idx in zip(required_keys, indices_fallback):
        if key not in col_map and len(raw_df.columns) > idx:
            col_map[key] = raw_df.columns[idx]

    games_list = []

    # Process data matrices
    for _, row in raw_df.iterrows():
        a_team = str(row[col_map['away_team']]).strip()
        h_team = str(row[col_map['home_team']]).strip()
        
        if not a_team or not h_team or 'team' in a_team.lower() or 'nan' in a_team.lower():
            continue
            
        try:
            a_proj = float(str(row[col_map['away_proj']]).strip())
            h_proj = float(str(row[col_map['home_proj']]).strip())
            a_odds = row[col_map['away_odds']]
            h_odds = row[col_map['home_odds']]
        except:
            continue

        total_runs = a_proj + h_proj
        if total_runs <= 0:
            continue
            
        # Run differential math calculation engine
        model_away_p = a_proj / total_runs
        model_home_p = h_proj / total_runs
        vegas_away_p = parse_american_odds(a_odds)
        vegas_home_p = parse_american_odds(h_odds)
        
        away_ev = (model_away_p - vegas_away_p) * 100
        home_ev = (model_home_p - vegas_home_p) * 100

        games_list.append({
            'away': a_team, 'home': h_team, 'away_proj': a_proj, 'home_proj': h_proj,
            'away_odds': a_odds, 'home_odds': h_odds,
            'model_away_p': model_away_p, 'model_home_p': model_home_p,
            'vegas_away_p': vegas_away_p, 'vegas_home_p': vegas_home_p,
            'away_ev': away_ev, 'home_ev': home_ev
        })

    # Print Live Terminal Output Dashboard
    print("\n" + "="*75)
    print(" 📊 LIVE PRODUCTION MLB BETTING MODEL ANALYSIS")
    print("="*75)

    print("\n🎯 TOP VALUE FAVORITES")
    print("-" * 75)
    f_count = 0
    for g in games_list:
        if g['away_ev'] >= 4.0 and g['model_away_p'] > 0.52:
            print(f"• {g['away']} (Away) at {g['home']} | Edge: {g['away_ev']:+.2f}% EV")
            print(f"  ↳ True Probability: {g['model_away_p']:.1%} vs Market Implied: {g['vegas_away_p']:.1%}")
            f_count += 1
        if g['home_ev'] >= 4.0 and g['model_home_p'] > 0.52:
            print(f"• {g['home']} (Home) vs. {g['away']} | Edge: {g['home_ev']:+.2f}% EV")
            print(f"  ↳ True Probability: {g['model_home_p']:.1%} vs Market Implied: {g['vegas_home_p']:.1%}")
            f_count += 1
    if f_count == 0:
        print("  No current matchups qualify under favorite value edge targets.")

    print("\n🐶 LIVE VALUE UNDERDOGS & SQUADS")
    print("-" * 75)
    u_count = 0
    for g in games_list:
        if g['away_ev'] >= 2.0 and g['vegas_away_p'] <= 0.51:
            print(f"• {g['away']} (Away) at {g['home']} [Line: {g['away_odds']}] | Edge: {g['away_ev']:+.2f}% EV")
            u_count += 1
        if g['home_ev'] >= 2.0 and g['vegas_home_p'] <= 0.51:
            print(f"• {g['home']} (Home) vs. {g['away']} [Line: {g['home_odds']}] | Edge: {g['home_ev']:+.2f}% EV")
            u_count += 1
    if u_count == 0:
        print("  No current plus-money matchups present a calculated data discrepancy.")
    print("="*75)

if __name__ == "__main__":
    run_mlb_live_sheet_model()
