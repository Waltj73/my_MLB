import pandas as pd
import requests
import io
import sys

def parse_odds(odds_val):
    """Converts American moneyline odds (e.g., '+114', '-137') to implied probability."""
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

def parse_game_blocks():
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    print("🔄 Connecting to live sheet engine...")
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla"}, timeout=10)
        response.raise_for_status()
        # Read without headers to navigate the stacked blocks by exact coordinate positions
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

    games_list = []
    total_rows = len(df)

    # Scan through the sheet looking for the start of each game block
    for i in range(total_rows - 1):
        row_str = str(df.iloc[i, 0]).strip().lower()
        
        # Identify the anchor point (e.g., 'Game1', 'Game 2', 'Game3')
        if row_str.startswith('game'):
            try:
                # Away Data (Row i+1)
                away_team = str(df.iloc[i+1, 1]).strip()
                away_odds = df.iloc[i+1, 4]  # Column E (Moneyline)
                away_win_pct = str(df.iloc[i+1, 15]).strip()  # Column P (Calc Win%)

                # Home Data (Row i+2)
                home_team = str(df.iloc[i+2, 1]).strip()
                home_odds = df.iloc[i+2, 4]  # Column E (Moneyline)
                home_win_pct = str(df.iloc[i+2, 15]).strip()  # Column P (Calc Win%)

                # Clean up percentage string from sheet (e.g. '43.55%' -> 0.4355)
                model_away_p = float(away_win_pct.replace('%', '').strip()) / 100.0
                model_home_p = float(home_win_pct.replace('%', '').strip()) / 100.0

                # Calculate Vegas implied numbers
                vegas_away_p = parse_odds(away_odds)
                vegas_home_p = parse_odds(home_odds)

                # Calculate Expected Value Edge
                away_ev = (model_away_p - vegas_away_p) * 100
                home_ev = (model_home_p - vegas_home_p) * 100

                games_list.append({
                    'away': away_team, 'home': home_team,
                    'away_odds': away_odds, 'home_odds': home_odds,
                    'model_away_p': model_away_p, 'model_home_p': model_home_p,
                    'vegas_away_p': vegas_away_p, 'vegas_home_p': vegas_home_p,
                    'away_ev': away_ev, 'home_ev': home_ev
                })
            except Exception as e:
                # Silently skip incomplete blocks or formatting rows
                continue

    # Console Output Dashboard
    print("\n" + "="*75)
    print(" 📊 LIVE PRODUCTION MLB BETTING MODEL TARGETS")
    print("="*75)

    print("\n🎯 TOP VALUE FAVORITES")
    print("-" * 75)
    f_count = 0
    for g in games_list:
        if g['away_ev'] >= 4.0 and g['model_away_p'] > 0.52:
            print(f"• {g['away']} (Away) at {g['home']} | Edge: {g['away_ev']:+.2f}% EV")
            print(f"  ↳ Model Prob: {g['model_away_p']:.1%} vs Market Implied: {g['vegas_away_p']:.1%}")
            f_count += 1
        if g['home_ev'] >= 4.0 and g['model_home_p'] > 0.52:
            print(f"• {g['home']} (Home) vs. {g['away']} | Edge: {g['home_ev']:+.2f}% EV")
            print(f"  ↳ Model Prob: {g['model_home_p']:.1%} vs Market Implied: {g['vegas_home_p']:.1%}")
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
        print("  No current plus-money matchups present a calculated edge.")
    print("="*75 + "\n")

if __name__ == "__main__":
    parse_game_blocks()
