import pandas as pd
import numpy as np

def fetch_and_analyze_mlb():
    # Public CSV export link for your specific Google Sheet and GID
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid = "1240994733"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    print("🔄 Fetching live data from MLB Matchups Sheet...")
    try:
        # Read data starting from Row 2 (index 1) to bypass the main title row if present, 
        # or read directly if standard format.
        df = pd.read_csv(csv_url)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    # Clean up column names (remove leading/trailing spaces and lowercase them for robust matching)
    df.columns = df.columns.str.strip().str.lower()
    
    # ─── MAPPING EXPECTED COLUMNS ───
    # We dynamically find the right columns even if naming varies slightly
    col_mapping = {
        'away': ['away', 'away team', 'away_team', 'visitor'],
        'home': ['home', 'home team', 'home_team', 'local'],
        'away_proj': ['away proj', 'away projected runs', 'away_projected', 'away_proj_runs'],
        'home_proj': ['home proj', 'home projected runs', 'home_projected', 'home_proj_runs'],
        'vegas_away': ['vegas away', 'away odds', 'away line', 'vegas_away_line'],
        'vegas_home': ['vegas home', 'home odds', 'home line', 'vegas_home_line']
    }
    
    final_cols = {}
    for standard_name, options in col_mapping.items():
        matched = [col for col in df.columns if col in options]
        if matched:
            final_cols[standard_name] = matched[0]
        else:
            # Fallback to structural positioning if named columns aren't matched cleanly
            if standard_name == 'away': final_cols[standard_name] = df.columns[0]
            elif standard_name == 'home': final_cols[standard_name] = df.columns[1]
            elif standard_name == 'away_proj': final_cols[standard_name] = df.columns[2]
            elif standard_name == 'home_proj': final_cols[standard_name] = df.columns[3]
            elif standard_name == 'vegas_away': final_cols[standard_name] = df.columns[4]
            elif standard_name == 'vegas_home': final_cols[standard_name] = df.columns[5]

    # Clean data rows (drop rows where team names or key metrics are missing)
    df = df.dropna(subset=[final_cols['away'], final_cols['home']])
    
    # Helper function to convert American Odds to Implied Probability
    def odds_to_prob(odds):
        try:
            odds = float(str(odds).replace('+', '').strip())
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        except:
            return 0.50  # Default fallback if line is unreadable

    results = []

    for _, row in df.iterrows():
        away_team = str(row[final_cols['away']]).strip()
        home_team = str(row[final_cols['home']]).strip()
        
        # Skip header duplicates or empty placeholder rows
        if "team" in away_team.lower() or away_team == "":
            continue
            
        try:
            # Parse metrics safely
            a_proj = float(row[final_cols['away_proj']])
            h_proj = float(row[final_cols['home_proj']])
            v_away = row[final_cols['vegas_away']]
            v_home = row[final_cols['vegas_home']]
        except Exception:
            # Skip rows that don't contain valid numeric projection figures yet
            continue

        # ─── METRIC ENGINE ───
        # 1. Calculate Model True Win Probabilities based on custom run differentials
        total_proj_runs = a_proj + h_proj
        if total_proj_runs > 0:
            model_away_prob = a_proj / total_proj_runs
            model_home_prob = h_proj / total_proj_runs
        else:
            model_away_prob, model_home_prob = 0.50, 0.50

        # 2. Get Vegas Implied Probabilities
        vegas_away_prob = odds_to_prob(v_away)
        vegas_home_prob = odds_to_prob(v_home)

        # 3. Calculate Expected Value (EV) Discrepancies
        away_ev = (model_away_prob - vegas_away_prob) * 100
        home_ev = (model_home_prob - vegas_home_prob) * 100

        # Package data for analysis
        results.append({
            'Away': away_team, 'Home': home_team,
            'Away Proj': a_proj, 'Home Proj': h_proj,
            'Vegas Away': v_away, 'Vegas Home': v_home,
            'Away Model Prob': model_away_prob, 'Home Model Prob': model_home_prob,
            'Away Vegas Prob': vegas_away_prob, 'Home Vegas Prob': vegas_home_prob,
            'Away EV': away_ev, 'Home EV': home_ev
        })

    # ─── ANALYTICAL OUTPUT REPORTING ───
    print("\n" + "="*70)
    print(" 📊 LIVE MLB BETTING MODEL ANALYSIS & INSIGHTS")
    print("="*70)

    # 1. Filter Top Value Favorites (Model favors team, and price holds clear positive EV)
    print("\n🎯 TOP VALUE FAVORITES (Market Discrepancy Picks)")
    print("-" * 70)
    fav_found = False
    for match in results:
        # Identify if Away or Home is the calculated value choice
        if match['Away EV'] > 5 and match['Away Model Prob'] > 0.55:
            print(f"• {match['Away']} (at {match['Home']})")
            print(f"  ↳ True Odds Projection: {match['Away Model Prob']:.1%} | Vegas Implied: {match['Away Vegas Prob']:.1%}")
            print(f"  ↳ Edge: {match['Away EV']:+.2f}% Win Probability Discrepancy")
            print(f"  ↳ Why: Model projects a clear {match['Away Proj']:.1f} to {match['Home Proj']:.1f} run margin.")
            fav_found = True
        if match['Home EV'] > 5 and match['Home Model Prob'] > 0.55:
            print(f"• {match['Home']} (vs. {match['Away']})")
            print(f"  ↳ True Odds Projection: {match['Home Model Prob']:.1%} | Vegas Implied: {match['Home Vegas Prob']:.1%}")
            print(f"  ↳ Edge: {match['Home EV']:+.2f}% Win Probability Discrepancy")
            print(f"  ↳ Why: Home advantage coupled with a {match['Home Proj']:.1f} to {match['Away Proj']:.1f} run projection.")
            fav_found = True
    if not fav_found:
        print("  No heavy favorites currently meet the high-threshold EV requirements today.")

    # 2. Filter Live Underdogs/Pick'ems
    print("\n🐶 LIVE VALUE UNDERDOGS & SPLIT SQUADS")
    print("-" * 70)
    dog_found = False
    for match in results:
        # Checking for positive expected value where market implied probability is lower/underdog status
        if match['Away EV'] > 3 and match['Away Vegas Prob'] <= 0.51:
            print(f"• {match['Away']} (at {match['Home']}) [Line: {match['Vegas Away']}]")
            print(f"  ↳ True Odds Projection: {match['Away Model Prob']:.1%} | Vegas Implied: {match['Away Vegas Prob']:.1%}")
            print(f"  ↳ Edge: {match['Away EV']:+.2f}% Expected Value")
            print(f"  ↳ Why: Market implies sub-50% odds, but custom metrics show a {match['Away Proj']:.1f} run projection capability.")
            dog_found = True
        if match['Home EV'] > 3 and match['Home Vegas Prob'] <= 0.51:
            print(f"• {match['Home']} (vs. {match['Away']}) [Line: {match['Vegas Home']}]")
            print(f"  ↳ True Odds Projection: {match['Home Model Prob']:.1%} | Vegas Implied: {match['Home Vegas Prob']:.1%}")
            print(f"  ↳ Edge: {match['Home EV']:+.2f}% Expected Value")
            print(f"  ↳ Why: Plus-money pricing or flat pick'em line completely ignores the local {match['Home Proj']:.1f} to {match['Away Proj']:.1f} model run margin.")
            dog_found = True
    if not dog_found:
        print("  No underdog plays met raw positive EV conditions based on active data.")

    print("\n" + "="*70)

if __name__ == "__main__":
    fetch_and_analyze_mlb()
