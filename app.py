import pandas as pd
import numpy as np
import sys

def parse_american_odds(odds_val):
    """Converts American odds strings or numbers safely to a probability fraction."""
    try:
        val_str = str(odds_val).replace('+', '').strip()
        # Handle cases where empty strings or placeholders slip through
        if not val_str or any(x in val_str.lower() for x in ['vs', 'at', '@', 'nan', 'null']):
            return 0.50
        num = float(val_str)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def build_mlb_dashboard():
    # Production sheet endpoints forced to CSV format
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    print("🔄 Establishing connection to Google Sheet Engine...")
    try:
        # Load data cleanly without assuming header positions immediately
        raw_df = pd.read_csv(url)
    except Exception as e:
        print(f"❌ Connection failed: Unable to parse remote CSV link. ({e})")
        sys.exit(1)
        
    # Standardize column labels to remove human formatting discrepancies
    raw_df.columns = raw_df.columns.str.strip().str.lower()
    
    # Precise signature identification for your specific model structure
    col_map = {}
    for col in raw_df.columns:
        if 'away' in col or 'team 1' in col:
            if 'proj' in col or 'run' in col: col_map['away_proj'] = col
            elif 'line' in col or 'odds' in col or 'vegas' in col: col_map['away_odds'] = col
            else: col_map['away_team'] = col
        elif 'home' in col or 'team 2' in col:
            if 'proj' in col or 'run' in col: col_map['home_proj'] = col
            elif 'line' in col or 'odds' in col or 'vegas' in col: col_map['home_odds'] = col
            else: col_map['home_team'] = col

    # Bulletproof fallback using structural indices if exact string match fails
    required_keys = ['away_team', 'home_team', 'away_proj', 'home_proj', 'away_odds', 'home_odds']
    indices_fallback = [0, 1, 2, 3, 4, 5]
    for key, idx in zip(required_keys, indices_fallback):
        if key not in col_map and len(raw_df.columns) > idx:
            col_map[key] = raw_df.columns[idx]

    # Verify column layout viability before executing matrix math
    if len(col_map) < 6:
        print("❌ Data Layout Mismatch: Sheet formatting does not match standard 6-column projection structure.")
        sys.exit(1)

    games_list = []

    # Parse structural contents line by line
    for _, row in raw_df.iterrows():
        a_team = str(row[col_map['away_team']]).strip()
        h_team = str(row[col_map['home_team']]).strip()
        
        # Skip labels, empty records, and visual summary rows
        if not a_team or not h_team or 'team' in a_team.lower() or 'nan' in a_team.lower():
            continue
            
        try:
            a_proj = float(str(row[col_map['away_proj']]).strip())
            h_proj = float(str(row[col_map['home_proj']]).strip())
            a_odds = row[col_map['away_odds']]
            h_odds = row[col_map['home_odds']]
        except:
            # Silently pass incomplete rows that lack active quantitative parameters
            continue

        # Mathematical Execution Engine
        total_runs = a_proj + h_proj
        if total_runs <= 0:
            continue
            
        # 1. Calculated Model Probabilities
        model_away_p = a_proj / total_runs
        model_home_p = h_proj / total_runs
        
        # 2. Implied Vegas Line Probabilities
        vegas_away_p = parse_american_odds(a_odds)
        vegas_home_p = parse_american_odds(h_odds)
        
        # 3. True Discrepancy Margin (Expected Value % Edge)
        away_ev = (model_away_p - vegas_away_p) * 100
        home_ev = (model_home_p - vegas_home_p) * 100

        games_list.append({
            'away': a_team, 'home': h_team, 'away_proj': a_proj, 'home_proj': h_proj,
            'away_odds': a_odds, 'home_odds': h_odds,
            'model_away_p': model_away_p, 'model_home_p': model_home_p,
            'vegas_away_p': vegas_away_p, 'vegas_home_p': vegas_home_p,
            'away_ev': away_ev, 'home_ev': home_ev
        })

    # Output Analytical Dashboard directly to the user console Terminal
    print("\n" + "="*75)
    print(" 📊 PRODUCTION MLB BETTING MODEL TARGETS")
    print("="*75)

    # Filter Strategy A: Top Calculated Favorites (True Favorite Value)
    print("\n🎯 TOP VALUE FAVORITES")
    print("-" * 75)
    f_count = 0
    for g in games_list:
        if g['away_ev'] >= 4.0 and g['model_away_p'] > 0.52:
            print(f"• {g['away']} (Away) at {g['home']}")
            print(f"  ↳ Model True Probability: {g['model_away_p']:.1%} | Market Implied: {g['vegas_away_p']:.1%}")
            print(f"  ↳ Measured Value Edge: {g['away_ev']:+.2f}% EV")
            print(f"  ↳ Analytics: Model projects a clear {g['away_proj']:.1f} to {g['home_proj']:.1f} score margin.")
            f_count += 1
        if g['home_ev'] >= 4.0 and g['model_home_p'] > 0.52:
            print(f"• {g['home']} (Home) vs. {g['away']}")
            print(f"  ↳ Model True Probability: {g['model_home_p']:.1%} | Market Implied: {g['vegas_home_p']:.1%}")
            print(f"  ↳ Measured Value Edge: {g['home_ev']:+.2f}% EV")
            print(f"  ↳ Analytics: Model projects a clear {g['home_proj']:.1f} to {g['away_proj']:.1f} score margin.")
            f_count += 1
    if f_count == 0:
        print("  No current matchups qualify under strict favorite value edge targets.")

    # Filter Strategy B: Top Calculated Underdogs / Pick'ems
    print("\n🐶 LIVE VALUE UNDERDOGS & SQUADS")
    print("-" * 75)
    u_count = 0
    for g in games_list:
        if g['away_ev'] >= 2.0 and g['vegas_away_p'] <= 0.51:
            print(f"• {g['away']} (Away) at {g['home']} [Line: {g['away_odds']}]")
            print(f"  ↳ Model True Probability: {g['model_away_p']:.1%} | Market Implied: {g['vegas_away_p']:.1%}")
            print(f"  ↳ Measured Value Edge: {g['away_ev']:+.2f}% EV")
            print(f"  ↳ Analytics: Line underprices squad capabilities against projected {g['home_proj']:.1f} home defense.")
            u_count += 1
        if g['home_ev'] >= 2.0 and g['vegas_home_p'] <= 0.51:
            print(f"• {g['home']} (Home) vs. {g['away']} [Line: {g['home_odds']}]")
            print(f"  ↳ Model True Probability: {g['model_home_p']:.1%} | Market Implied: {g['vegas_home_p']:.1%}")
            print(f"  ↳ Measured Value Edge: {g['home_ev']:+.2f}% EV")
            print(f"  ↳ Analytics: Line underprices squad capabilities against projected {g['away_proj']:.1f} away offense.")
            u_count += 1
    if u_count == 0:
        print("  No current plus-money or pick'em matchups present a calculated data discrepancy.")

    print("\n" + "="*75)

if __name__ == "__main__":
    build_mlb_dashboard()
