import pandas as pd
import requests
import io
import sys

def parse_american_odds(odds_val):
    """Safely converts betting lines (+114, -137) to implied probability fractions."""
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

def run_mlb_model():
    print("\n" + "="*75)
    print(" 🔄 CONNECTING TO MLB DATABASE STREAM...")
    print("="*75)

    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        response.raise_for_status()
        raw_text = response.text
    except Exception as e:
        print(f"❌ CONNECTION ERROR: Unable to download sheet data. ({e})")
        sys.exit(1)

    # --- PART 1: EXTRACT CALC WIN PERCENTAGES FROM THE TEXT DUMP ---
    # Find all occurrences of team acronyms followed by their exact model percentage
    # Example: PHI043.55%, ARI076.00%, WSn047.01%
    win_percentages = {}
    import re
    pct_matches = re.findall(r'([A-Za-z]{3})0(\d+\.\d+)\%', raw_text)
    for team_code, pct_val in pct_matches:
        # Standardize team identifiers to match up with the grid names later
        team_key = team_code.upper().strip()
        # Handle unique 3-letter sheet tags if necessary
        if team_key == "WSN": team_key = "WSH" 
        win_percentages[team_key] = float(pct_val) / 100.0

    # --- PART 2: PROCESS THE SPREADTOTALS DATA GRID AT THE BOTTOM ---
    lines = raw_text.splitlines()
    grid_rows = []
    start_processing = False
    
    for line in lines:
        if "spreadtotalsmoneyline" in line.lower().replace(" ", "") or "mlb - friday" in line.lower():
            start_processing = True
            continue
        if start_processing:
            if line.strip() and not line.startswith("Spread") and not line.startswith("0000"):
                grid_rows.append(line)

    if not grid_rows:
        # Fallback: If split indicator fails, read the full stream cleanly via pandas matrices
        df_fallback = pd.read_csv(io.StringIO(raw_text), header=None)
        grid_rows = [",".join(map(str, row)) for _, row in df_fallback.iterrows()]

    # Re-read the isolated bottom grid into a structured dataframe
    grid_csv = "\n".join(grid_rows)
    df = pd.read_csv(io.StringIO(grid_csv), header=None)

    print(f"📊 Analyzing active matchup grids...")
    print("\n" + "="*75)
    print(" 🎯 CALCULATING LIVE EXPECTED VALUE (EV) TARGETS")
    print("="*75)

    success_count = 0

    # Step through the spreadsheet rows in pairs (Row 1 = Away, Row 2 = Home)
    idx = 0
    while idx < len(df) - 1:
        try:
            # Slicing team names and cleaning up artifacts
            away_raw = str(df.iloc[idx, 0]).replace('↺', '').strip()
            home_raw = str(df.iloc[idx+1, 0]).replace('↺', '').strip()
            
            # Skip metadata, titles, or summary cells
            if any(x in away_raw.lower() for x in ['spread', 'totals', 'handle', 'nan', 'game', 'may']):
                idx += 1
                continue

            # Strip location labels for clean parsing matching
            away_name = away_raw.split('1')[-1].strip()
            home_name = home_raw.split('1')[-1].strip()

            # Identify the 3-letter abbreviation code to link back to the model's win percentages
            away_code = away_name[:3].upper()
            home_code = home_name[:3].upper()

            # Grab your model's calculated win probabilities
            model_away_p = win_percentages.get(away_code, 0.50)
            model_home_p = win_percentages.get(home_code, 0.50)

            # Extract betting lines from Column E (Index 4)
            away_odds = df.iloc[idx, 4]
            home_odds = df.iloc[idx+1, 4]

            # Calculate Vegas implied probabilities
            vegas_away_p = parse_american_odds(away_odds)
            vegas_home_p = parse_american_odds(home_odds)

            # Calculate the explicit Expected Value Edge
            away_ev = (model_away_p - vegas_away_p) * 100
            home_ev = (model_home_p - vegas_home_p) * 100

            print(f"\n⚾ MATCHUP: {away_name} ({away_odds}) @ {home_name} ({home_odds})")
            print(f"  ↳ Away Model Prob: {model_away_p:.2%} | Market Implied: {vegas_away_p:.2%} | Edge: {away_ev:+.2f}% EV")
            print(f"  ↳ Home Model Prob: {model_home_p:.2%} | Market Implied: {vegas_home_p:.2%} | Edge: {home_ev:+.2f}% EV")
            
            if away_ev >= 4.0:
                print(f"  🔥 STRATEGY PLAY: Positive Value on {away_name} (Away)")
            if home_ev >= 4.0:
                print(f"  🔥 STRATEGY PLAY: Positive Value on {home_name} (Home)")
                
            success_count += 1
            idx += 2 # Advance past the processed 2-row game block
        except Exception as e:
            idx += 1
            continue

    if success_count == 0:
        print("\n❌ SYSTEM REPORT: No matchups could be paired. The layout mapping is still out of alignment.")
    print("\n" + "="*75 + "\n")

if __name__ == "__main__":
    run_mlb_model()
