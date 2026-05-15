import pandas as pd
import requests
import io
import sys

def parse_line_to_percentage(line_value):
    """Safely handles converting American betting lines to implied probabilities."""
    try:
        cleaned = str(line_value).replace('+', '').strip()
        if not cleaned or any(char in cleaned.lower() for char in ['vs', 'at', '@', 'nan', 'team', 'pk']):
            return 0.50
        num = float(cleaned)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def run_terminal_mlb_model():
    # Print immediately so you know the script is alive and executing
    print("\n=======================================================")
    print("🚀 INIT: Starting Local Math Engine Script...")
    print("=======================================================\n")
    
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    print("🔄 Step 1: Requesting raw data from Google Sheet...")
    try:
        # Strict 5-second timeout ensures the script CANNOT sit on a blank screen forever
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        response.raise_for_status()
        print("✅ Step 2: Data received. Slicing structural grid...")
        
        # Treat headers as pure positional numbers to bypass name mismatches
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except requests.exceptions.Timeout:
        print("\n❌ TIMEOUT FAILURE: Google is ghosting the connection and refused to send data.")
        print("Please check your internet connection or verify the spreadsheet link's sharing privacy.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL NETWORK ERROR: {e}")
        sys.exit(1)

    games_list = []

    print(f"📊 Step 3: Analyzing {len(df)} lines for valid matchup sets...")
    
    for idx, row in df.iterrows():
        if len(row) < 6:
            continue
            
        away_team = str(row[0]).strip()
        home_team = str(row[1]).strip()
        
        # Sift out text descriptions or empty placeholders
        if not away_team or 'nan' in away_team.lower() or 'team' in away_team.lower() or 'away' in away_team.lower():
            continue
        if not home_team or 'nan' in home_team.lower() or 'home' in home_team.lower():
            continue

        try:
            # Map values by absolute structural position
            away_proj = float(str(row[2]).strip())
            home_proj = float(str(row[3]).strip())
            vegas_away = row[4]
            vegas_home = row[5]
            
            total_runs = away_proj + home_proj
            if total_runs <= 0:
                continue

            # Calculate Model Probabilities
            model_away_prob = away_proj / total_runs
            model_home_prob = home_proj / total_runs
            
            vegas_away_prob = parse_line_to_percentage(vegas_away)
            vegas_home_prob = parse_line_to_percentage(vegas_home)
            
            # Expected Value Calculations (P14 Engine Matrix Alignment)
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
            continue

    # Final Summary Terminal Report
    print("\n" + "="*75)
    print(" 📊 FINAL MLB MODEL OUTPUT REPORT")
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
        print("  No current matchups qualify under favorite edge thresholds.")

    print("\n🐶 LIVE VALUE UNDERDOGS")
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
        print("  No current underdogs present an actionable data discrepancy.")
    print("="*75 + "\n")

if __name__ == "__main__":
    run_terminal_mlb_model()
