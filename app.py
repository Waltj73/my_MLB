import pandas as pd
import requests
import io
import sys

def parse_american_odds(odds_val):
    """Safely converts betting lines (e.g. -145, +120) to implied probability."""
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

def run_flawless_mlb_model():
    sheet_id = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
    gid_id = "1240994733"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("🔄 Connecting to live sheet...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        # Read raw strings, ignoring initial blank lines completely
        df = pd.read_csv(io.StringIO(response.text), header=None)
    except Exception as e:
        print(f"❌ Connection Blocked by Google: {e}")
        sys.exit(1)

    # --- ADAPTIVE DATA SCANNER ---
    # Look for the row that actually contains team indicators to establish real data headers
    header_row_idx = 0
    for idx, row in df.iterrows():
        row_str = " ".join(row.dropna().astype(str)).lower()
        if 'team' in row_str or 'proj' in row_str or 'away' in row_str or 'home' in row_str:
            header_row_idx = idx
            break

    # Re-align dataframe using the discovered true data matrix row
    df.columns = df.iloc[header_row_idx].str.strip().str.lower()
    df = df.iloc[header_row_idx + 1:].reset_index(drop=True)

    # Track column names based on structural content signatures
    cols = {}
    for col in df.columns:
        if pd.isna(col): continue
        c_name = str(col).strip().lower()
        if 'away' in c_name or 'visitor' in c_name or 'team 1' in c_name:
            if 'proj' in c_name or 'run' in c_name: cols['away_proj'] = col
            elif 'odds' in c_name or 'line' in c_name or 'vegas' in c_name: cols['away_odds'] = col
            else: cols['away_team'] = col
        elif 'home' in c_name or 'local' in c_name or 'team 2' in c_name:
            if 'proj' in c_name or 'run' in c_name: cols['home_proj'] = col
            elif 'odds' in c_name or 'line' in c_name or 'vegas' in c_name: cols['home_odds'] = col
            else: cols['home_team'] = col

    # Hard structural index backup if custom column text matches fail completely
    fallback_keys = ['away_team', 'home_team', 'away_proj', 'home_proj', 'away_odds', 'home_odds']
    for i, key in enumerate(fallback_keys):
        if key not in cols and len(df.columns) > i:
            cols[key] = df.columns[i]

    games_list = []

    # Processing values loop
    for _, row in df.iterrows():
        try:
            a_team = str(row[cols['away_team']]).strip()
            h_team = str(row[cols['home_team']]).strip()
            
            if not a_team or 'nan' in a_team.lower() or 'team' in a_team.lower() or a_team == "":
                continue

            a_proj = float(str(row[cols['away_proj']]).strip())
            h_proj = float(str(row[cols['home_proj']]).strip())
            a_odds = row[cols['away_odds']]
            h_odds = row[cols['home_odds']]
            
            total_runs = a_proj + h_proj
            if total_runs <= 0: continue

            # Calculations Engine
            model_away_p = a_proj / total_runs
            model_home_p = h_proj / total_runs
            vegas_away_p = parse_american_odds(a_odds)
            vegas_home_p = parse_american_odds(h_odds)
            
            # Column P14 represents EV calculation directly
            away_ev = (model_away_p - vegas_away_p) * 100
            home_ev = (model_home_p - vegas_home_p) * 100

            games_list.append({
                'away': a_team, 'home': h_team, 'away_proj': a_proj, 'home_proj': h_proj,
                'away_odds': a_odds, 'home_odds': h_odds,
                'model_away_p': model_away_p, 'model_home_p': model_home_p,
                'vegas_away_p': vegas_away_p, 'vegas_home_p': vegas_home_p,
                'away_ev': away_ev, 'home_ev': home_ev
            })
        except:
            continue

    # Console Presentation UI Terminal Block
    print("\n" + "="*75)
    print(" 📊 SYSTEM DEPLOYMENT: MLB MODEL PROCESSING COMPLETED")
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
        print("  No current plus-money matchups present a calculated edge.")
    print("="*75)

if __name__ == "__main__":
    run_flawless_mlb_model()
