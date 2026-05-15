import pandas as pd
import requests
import io
import sys

def parse_line_probability(odds_input):
    """Safely handles converting American betting lines to implied percentages."""
    try:
        cleaned = str(odds_input).replace('+', '').strip()
        if not cleaned or any(char in cleaned.lower() for char in ['vs', 'at', '@', 'nan', 'team', 'pk']):
            return 0.50
        num = float(cleaned)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def execute_mlb_model():
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print("🔄 Accessing live spreadsheet engine stream...")
    try:
        response = requests.get(url, headers=headers, timeout=12)
        response.raise_for_status()
        
        # Force pandas to ignore string headers entirely and treat columns as numbers (0, 1, 2, 3...)
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except Exception as e:
        print(f"❌ Connection Blocked: Unable to stream URL data. ({e})")
        sys.exit(1)

    games_list = []

    # Iterate through every single row, slicing by structural layout
    for idx, row in df.iterrows():
        # Clean potential empty formatting blocks
        if len(row) < 6:
            continue
            
        # Convert index objects to string names safely
        away_team = str(row[0]).strip()
        home_team = str(row[1]).strip()
        
        # Strict filter: skip text headers, empty spacers, or title blocks
        if not away_team or 'nan' in away_team.lower() or 'team' in away_team.lower() or 'away' in away_team.lower():
            continue
        if not home_team or 'nan' in home_team.lower() or 'home' in home_team.lower():
            continue

        try:
            # Absolute position mapping: Col 2 (Away Proj), Col 3 (Home Proj), Col 4 (Vegas Away), Col 5 (Vegas Home)
            away_proj = float(str(row[2]).strip())
            home_proj = float(str(row[3]).strip())
            vegas_away = row[4]
            vegas_home = row[5]
            
            total_runs = away_proj + home_proj
            if total_runs <= 0:
                continue

            # Probability Calculation Processing Engine
            model_away_prob = away_proj / total_runs
            model_home_prob = home_proj / total_runs
            
            vegas_away_prob = parse_line_probability(vegas_away)
            vegas_home_prob = parse_line_probability(vegas_home)
            
            # Calculating raw mathematical discrepancies (Column P14 EV Output Equivalent)
            away_ev = (model_away_prob - vegas_away_prob) * 100
            home_ev = (model_home_prob - vegas_home_prob) * 100

            games_list.append({
                'away': away_team, 'home': home_team, 
                'away_proj': away_proj, 'home_proj': home_proj,
                'vegas_away': vegas_away, 'vegas_home': vegas_home,
                'model_away_p': model_away_prob, 'model_home_p': model_home_prob,
                'vegas_away_p': vegas_away_prob, 'vegas_home_p': vegas_home_prob,
                'away_ev': away_ev, 'home_ev': home_ev
            })
        except:
            # Skip incomplete or non-numeric placeholder lines silently
            continue

    # Clean Console UI Report Display
    print("\n" + "="*75)
    print(" 📊 SYSTEM STATUS: SUCCESSFUL MLB AGGREGATION")
    print("="*75)

    print("\n🎯 TOP VALUE FAVORITES")
    print("-" * 75)
    f_count = 0
    for g in games_list:
        if g['away_ev'] >= 4.0 and g['model_away_p'] > 0.52:
            print(f"• {g['away']} (Away) at {g['home']} | Edge: {g['away_ev']:+.2f}% EV")
            print(f"  ↳ True Model Prob: {g['model_away_p']:.1%} vs Vegas Implied: {g['vegas_away_p']:.1%}")
            f_count += 1
        if g['home_ev'] >= 4.0 and g['model_home_p'] > 0.52:
            print(f"• {g['home']} (Home) vs. {g['away']} | Edge: {g['home_ev']:+.2f}% EV")
            print(f"  ↳ True Model Prob: {g['model_home_p']:.1%} vs Vegas Implied: {g['vegas_home_p']:.1%}")
            f_count += 1
    if f_count == 0:
        print("  No current matchups qualify under strict favorite value edge targets.")

    print("\n🐶 LIVE VALUE UNDERDOGS & SQUADS")
    print("-" * 75)
    u_count = 0
    for g in games_list:
        if g['away_ev'] >= 2.0 and g['vegas_away_p'] <= 0.51:
            print(f"• {g['away']} (Away) at {g['home']} [Line: {g['vegas_away']}] | Edge: {g['away_ev']:+.2f}% EV")
            u_count += 1
        if g['home_ev'] >= 2.0 and g['vegas_home_p'] <= 0.51:
            print(f"• {g['home']} (Home) vs. {g['away']} [Line: {g['vegas_home']}] | Edge: {g['home_ev']:+.2f}% EV")
            u_count += 1
    if u_count == 0:
        print("  No current plus-money matchups present a calculated edge.")
    print("="*75)

if __name__ == "__main__":
    execute_mlb_model()
