import pandas as pd
import requests
import io
import re
import sys

def parse_line_probability(odds_input):
    """Safely converts American betting lines (+114, -137) to implied probability."""
    try:
        cleaned = str(odds_input).replace('+', '').strip()
        if not cleaned or any(char in cleaned.lower() for char in ['vs', 'at', '@', 'nan', 'pk']):
            return 0.50
        num = float(cleaned)
        if num > 0:
            return 100 / (num + 100)
        else:
            return abs(num) / (abs(num) + 100)
    except:
        return 0.50

def run_mlb_stream_model():
    print("\n" + "="*75)
    print(" 🔄 MLB MODEL ENGINE: INITIALIZING DATA FETCH")
    print("="*75)

    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    try:
        # Requesting data with standard headers and a strict timeout to prevent hangs
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        # Read the raw stream as rows of data strings
        raw_rows = response.text.splitlines()
    except Exception as e:
        print(f"❌ NETWORK TIMEOUT OR ACCESS ERROR: {e}")
        sys.exit(1)

    games_list = []
    
    # Clean pattern to extract clumped strings: Captures Team Name, the Line (+/- numbers), and the Win % at the tail
    data_pattern = re.compile(r'(Away|Home)(.+?)([\+\-]\d+).*?(\d+\.\d+\%)')

    i = 0
    while i < len(raw_rows) - 2:
        current_line = raw_rows[i].strip()
        
        # Anchor the processing loop at the start of each game block
        if current_line.lower().startswith('game'):
            try:
                away_line = raw_rows[i+1].strip()
                home_line = raw_rows[i+2].strip()
                
                away_match = data_pattern.search(away_line)
                home_match = data_pattern.search(home_line)
                
                if away_match and home_match:
                    # Extract string tokens matching your text layout
                    away_team = away_match.group(2).strip()
                    away_odds = away_match.group(3).strip()
                    away_win_pct = float(away_match.group(4).replace('%', '')) / 100.0
                    
                    home_team = home_match.group(2).strip()
                    home_odds = home_match.group(3).strip()
                    home_win_pct = float(home_match.group(4).replace('%', '')) / 100.0
                    
                    # Convert betting lines to implied probability
                    vegas_away_prob = parse_line_probability(away_odds)
                    vegas_home_prob = parse_line_probability(home_odds)
                    
                    # Calculate Expected Value Edge (Your Column P14 equivalent)
                    away_ev = (away_win_pct - vegas_away_prob) * 100
                    home_ev = (home_win_pct - vegas_home_prob) * 100
                    
                    games_list.append({
                        'away': away_team, 'home': home_team,
                        'away_odds': away_odds, 'home_odds': home_odds,
                        'model_away_p': away_win_pct, 'model_home_p': home_win_pct,
                        'vegas_away_p': vegas_away_prob, 'vegas_home_p': vegas_home_prob,
                        'away_ev': away_ev, 'home_ev': home_ev
                    })
                i += 3  # Move past this game block entirely
            except:
                i += 1
                continue
        else:
            i += 1

    # Printing Terminal Report Panel
    print("\n" + "="*75)
    print(" 📊 DATA ANALYSIS COMPLETED: ACTIVE TARGET MATCHUPS")
    print("="*75)

    if not games_list:
        print("❌ ERROR: Data rows failed to map. The sheet structure did not pass string filtering.")
        print("===========================================================================\n")
        return

    for g in games_list:
        print(f"\n⚾ MATCHUP: {g['away']} ({g['away_odds']}) @ {g['home']} ({g['home_odds']})")
        print(f"  ↳ Away Model: {g['model_away_p']:.2%} | Market Implied: {g['vegas_away_p']:.2%} | Edge: {g['away_ev']:+.2f}% EV")
        print(f"  ↳ Home Model: {g['model_home_p']:.2%} | Market Implied: {g['vegas_home_p']:.2%} | Edge: {g['home_ev']:+.2f}% EV")
        
        # Highlight high-value target positions
        if g['away_ev'] >= 4.0:
            print(f"  🔥 STRATEGY PLAY: Positive EV Edge on {g['away']} (Away)")
        if g['home_ev'] >= 4.0:
            print(f"  🔥 STRATEGY PLAY: Positive EV Edge on {g['home']} (Home)")

    print("\n" + "="*75 + "\n")

if __name__ == "__main__":
    run_mlb_stream_model()
