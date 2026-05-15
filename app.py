import pandas as pd
import numpy as np
import sys

def calculate_american_odds_probability(odds_value):
    """
    Converts American betting odds (e.g., -150, +130) into an implied probability percentage.
    """
    try:
        # Clean up input string/number
        cleaned_odds = float(str(odds_value).replace('+', '').strip())
        if cleaned_odds > 0:
            return 100 / (cleaned_odds + 100)
        else:
            return abs(cleaned_odds) / (abs(cleaned_odds) + 100)
    except Exception:
        # Default fallback to 50% if the odds data is missing or unreadable
        return 0.50

def run_mlb_betting_model():
    # Target Google Sheet Parameters
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    
    # Correct URL structure to force a direct CSV download of the specific tab
    csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    print("🔄 Connecting to Google Sheet and downloading live matchups...")
    
    try:
        # Download the live sheet data directly into a pandas DataFrame
        df = pd.read_csv(csv_export_url)
    except Exception as e:
        print("\n❌ CRITICAL ERROR: Could not access or download the Google Sheet.")
        print(f"Details: {e}")
        print("\n💡 Fix: Make sure the Google Sheet is set to 'Anyone with the link can view' so the script can read it.")
        sys.exit(1)
        
    # Standardize column headers: remove spaces, force lowercase
    df.columns = df.columns.str.strip().str.lower()
    
    # Define dynamic keyword groupings to find correct columns regardless of slight structural changes
    potential_away_cols = ['away', 'away team', 'away_team', 'visitor', 'v']
    potential_home_cols = ['home', 'home team', 'home_team', 'local', 'h']
    potential_away_proj = ['away proj', 'away projected runs', 'away_projected', 'away_proj', 'away_proj_runs']
    potential_home_proj = ['home proj', 'home projected runs', 'home_projected', 'home_proj', 'home_proj_runs']
    potential_vegas_away = ['vegas away', 'away odds', 'away line', 'vegas_away', 'vegas_away_line']
    potential_vegas_home = ['vegas home', 'home odds', 'home line', 'vegas_home', 'vegas_home_line']

    # Assign columns based on matching keywords, falling back to positional index if matches aren't found
    matched_cols = {}
    matched_cols['away'] = next((c for c in df.columns if c in potential_away_cols), df.columns[0])
    matched_cols['home'] = next((c for c in df.columns if c in potential_home_cols), df.columns[1])
    matched_cols['away_proj'] = next((c for c in df.columns if c in potential_away_proj), df.columns[2])
    matched_cols['home_proj'] = next((c for c in df.columns if c in potential_home_proj), df.columns[3])
    matched_cols['vegas_away'] = next((c for c in df.columns if c in potential_vegas_away), df.columns[4])
    matched_cols['vegas_home'] = next((c for c in df.columns if c in potential_vegas_home), df.columns[5])

    # Drop completely blank rows based on team name availability
    df = df.dropna(subset=[matched_cols['away'], matched_cols['home']])
    
    processed_games = []

    # Iterate through every row of data in the spreadsheet
    for index, row in df.iterrows():
        away_team_raw = str(row[matched_cols['away']]).strip()
        home_team_raw = str(row[matched_cols['home']]).strip()
        
        # Skip header duplicates, empty rows, or summary metrics
        if not away_team_raw or "team" in away_team_raw.lower() or away_team_raw == "":
            continue
            
        try:
            # Parse metrics to floats
            away_projected_runs = float(row[matched_cols['away_proj']])
            home_projected_runs = float(row[matched_cols['home_proj']])
            vegas_away_odds = row[matched_cols['vegas_away']]
            vegas_home_odds = row[matched_cols['vegas_home']]
        except (ValueError, TypeError):
            # Skip rows that don't have valid numerical projections or data filled out yet
            continue

        # Core Mathematical Calculations
        total_projected_runs = away_projected_runs + home_projected_runs
        
        if total_projected_runs > 0:
            model_away_probability = away_projected_runs / total_projected_runs
            model_home_probability = home_projected_runs / total_projected_runs
        else:
            model_away_probability, model_home_probability = 0.50, 0.50

        # Calculate Vegas Implied Odds
        vegas_away_probability = calculate_american_odds_probability(vegas_away_odds)
        vegas_home_probability = calculate_american_odds_probability(vegas_home_odds)

        # Calculate Expected Value (EV) Discrepancy Margin
        away_expected_value = (model_away_probability - vegas_away_probability) * 100
        home_expected_value = (model_home_probability - vegas_home_probability) * 100

        processed_games.append({
            'away': away_team_raw,
            'home': home_team_raw,
            'away_proj': away_projected_runs,
            'home_proj': home_projected_runs,
            'vegas_away_odds': vegas_away_odds,
            'vegas_home_odds': vegas_home_odds,
            'model_away_prob': model_away_probability,
            'model_home_prob': model_home_probability,
            'vegas_away_prob': vegas_away_probability,
            'vegas_home_prob': vegas_home_probability,
            'away_ev': away_expected_value,
            'home_ev': home_expected_value
        })

    # Display Analytics Dashboard Report
    print("\n" + "="*75)
    print(" 📊 SYSTEM STATUS: SUCCESSFUL DATA AGGREGATION & ANALYSIS")
    print("="*75)

    if not processed_games:
        print("⚠ No valid matchup data could be processed. Please check your data formatting columns.")
        print("="*75)
        return

    # Section 1: Output Best Favorites (Strong model win probability paired with positive EV)
    print("\n🎯 TOP VALUE FAVORITES (Market Discrepancy High-Conviction)")
    print("-" * 75)
    favorites_count = 0
    for game in processed_games:
        if game['away_ev'] > 5.0 and game['model_away_prob'] > 0.55:
            print(f"• {game['away']} (Away) at {game['home']} (Home)")
            print(f"  ↳ True Model Target: {game['model_away_prob']:.1%} | Vegas Implied Line: {game['vegas_away_prob']:.1%}")
            print(f"  ↳ Statistical Edge: {game['away_ev']:+.2f}% Win Probability Advantage")
            print(f"  ↳ Analytics: Model projects a clear {game['away_proj']:.1f} to {game['home_proj']:.1f} run margin.")
            favorites_count += 1
        if game['home_ev'] > 5.0 and game['model_home_prob'] > 0.55:
            print(f"• {game['home']} (Home) vs. {game['away']} (Away)")
            print(f"  ↳ True Model Target: {game['model_home_prob']:.1%} | Vegas Implied Line: {game['vegas_home_prob']:.1%}")
            print(f"  ↳ Statistical Edge: {game['home_ev']:+.2f}% Win Probability Advantage")
            print(f"  ↳ Analytics: Model projects a clear {game['home_proj']:.1f} to {game['away_proj']:.1f} run margin.")
            favorites_count += 1
    if favorites_count == 0:
        print("  No matchups currently cross the threshold for clear favorite value picks.")

    # Section 2: Output Value Underdogs / Pick'ems
    print("\n🐶 LIVE VALUE UNDERDOGS (Plus-Money Advantage Picks)")
    print("-" * 75)
    underdogs_count = 0
    for game in processed_games:
        if game['away_ev'] > 3.0 and game['vegas_away_prob'] <= 0.51:
            print(f"• {game['away']} (Away) at {game['home']} (Home) [Line: {game['vegas_away_odds']}]")
            print(f"  ↳ True Model Target: {game['model_away_prob']:.1%} | Vegas Implied Line: {game['vegas_away_prob']:.1%}")
            print(f"  ↳ Statistical Edge: {game['away_ev']:+.2f}% Expected Value Margin")
            print(f"  ↳ Analytics: Market implies minor/dog odds, but model run score margin dictates a {game['away_proj']:.1f} performance capability.")
            underdogs_count += 1
        if game['home_ev'] > 3.0 and game['vegas_home_prob'] <= 0.51:
            print(f"• {game['home']} (Home) vs. {game['away']} (Away) [Line: {game['vegas_home_odds']}]")
            print(f"  ↳ True Model Target: {game['model_home_prob']:.1%} | Vegas Implied Line: {game['vegas_home_prob']:.1%}")
            print(f"  ↳ Statistical Edge: {game['home_ev']:+.2f}% Expected Value Margin")
            print(f"  ↳ Analytics: Market implies minor/dog odds, but model run score margin dictates a {game['home_proj']:.1f} performance capability.")
            underdogs_count += 1
    if underdogs_count == 0:
        print("  No underdog/pick'em matchups currently cross the threshold for positive expected value.")

    print("\n" + "="*75)

if __name__ == "__main__":
    run_mlb_betting_model()
