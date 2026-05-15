import re

# Paste your raw text block inside these triple quotes
RAW_DATA_DUMP = """
Game16:40 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line6:40 PM ETCalc Win%AwayPhiladelphiaPhillies0+11421-23$-96622-20-244.73.88PHI043.55%HomePittsburghPirates0-137824-20$-8924-19-154.34.2-122PIT056.45%Game 28:40 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line8:40 PM ETAwayArizonaDiamondbacks0-12620-22$-10320-18-44.34.96.611OVARI076.00%HomeColoradoRockies0+10411.517-27$+ 7521-22-14.35.14.5136COL024.00%Game36:45 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line6:45 PM ETAwayTorontoBlue Jays0-13119-24$-1,25822-20-14.24.53.88TOR043.55%HomeDetroitTigers0+109819-25$-1,02920-21-24.24.44.2-121DET056.45%Game48:10 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line8:10 PM ETAwayTexasRangers0-11221-22$-20417-24-23.83.84.79TEX056.04%HomeHoustonAstros0-1088.517-28$-1,38028-16-14.65.64.3-102HOU043.96%Game56:45 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line6:45 PM ETAwayBaltimoreOrioles0-14220-24$-74825-18-14.45.24.79OVBAL052.99%HomeWashingtonNationals0+1189.521-23$+ 58328-13-35.45.84.5-106WSn047.01%Game67:10 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:10 PM ETAwayMiamiMarlins0+10220-24$-35425-17-22-14.24.53.58MIA034.25%HomeTampa BayRays0-123828-14$+ 1,44921-19-24.544.5-139TBR065.75%Game77:10 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:10 PM ETAwayCincinnatiReds0+11423-21$+ 3427-16-14.34.93.17.5OVCIN026.72%HomeClevelandGuardians0-137824-21$+ 26422-23-04.24.14.6-157CLE073.28%Game87:15 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:15 PM ETAwayNY YankeesYankees0-15727-17$-15017-24-35.13.53.87NYY062.12%HomeNY MetsMets0+130718-25$-1,86416-23-43.74.13.1115NYM037.88%Game97:15 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:15 PM ETAwayBostonRed Sox0+12918-25$-1,31919-23-13.743.37.5BOS033.82%HomeAtlantaBraves0-156830-14$+ 1,22818-23-35.43.34.3-143ATL066.18%Game107:40 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:40 PM ETAwayChi CubsCubs0-14928-16$+ 80722-18-4545.18.5OVCHC071.90%HomeChi SoxWhite Sox0+1248.522-21$+ 53824-19-04.44.63.6133CHW028.10%Game117:10 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line7:10 PM ETAwayMilwaukeeBrewers0-11024-17$+ 9520-20-15.13.65.19OVMIL064.61%HomeMinnesotaTwins0-110920-24$-26525-15-44.84.94.1114MIN035.39%Game128:15 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line8:15 PM ETAwayKansas CityRoyals0-10519-25$-1,03520-23-14.14.64.18.5OVKCR042.33%HomeSt. LouisCardinals0-1148.525-18$+ 1,13218-21-34.64.64.6-122STL057.67%Game139:38 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line9:38 PM ETAwayLA DodgersDodgers0-23226-18$-1,20718-25-14.93.46.510LAD085.76%HomeLA AngelsAngels0+188916-28$-91020-24-04.24.93.5175LAA014.24%Game149:40 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line9:40 PM ETAwaySan DiegoPadres0+11325-18$+ 38817-24-24.14.23.68UNSDP038.74%HomeSeattleMariners0-136722-23$-92619-24-24.23.94.3-128SEA061.26%Game159:40 PM ETMoneyOURecordProfitO-U-PRFRAEST ScoreEST Line9:40 PM ETAwaySF GiantsGiants0+11318-26$-61918-23-33.34.44.410SFG033.40%HomeSacramentoAthletics0-1361022-21$+ 22319-21-34.44.55.6-137ATH066.60%
"""

def parse_odds_to_prob(odds_str):
    try:
        num = float(odds_str.replace('+', ''))
        return 100 / (num + 100) if num > 0 else abs(num) / (abs(num) + 100)
    except:
        return 0.50

def parse_text_stream():
    # Break down the single wall of pasted text by line segments
    lines = RAW_DATA_DUMP.strip().split('\n')
    
    # Precise extraction regex built for your clumped string layout:
    # Captures: 1. Team Context Name, 2. Moneyline Odds (+/-), 3. Ending Win Percentage String
    team_regex = re.compile(r'(Away|Home)([A-Za-z\s\.\d]+?)([\+\-]\d+).*?(\d+\.\d+\%)')
    
    parsed_teams = []
    
    for line in lines:
        matches = team_regex.findall(line)
        for match in matches:
            role, name, odds, win_pct = match
            parsed_teams.append({
                'role': role.strip(),
                'name': name.strip(),
                'odds': odds.strip(),
                'win_p': float(win_pct.replace('%', '')) / 100.0
            })

    print("\n" + "="*75)
    print(" 📊 MLB VALUE REPORT (DIRECT RAW TEXT PARSER)")
    print("="*75)

    if len(parsed_teams) < 2:
        print("❌ Script could not extract structural patterns. Double check raw string paste entries.")
        print("="*75)
        return

    # Process pairs sequentially as Away/Home blocks
    for idx in range(0, len(parsed_teams) - 1, 2):
        try:
            away = parsed_teams[idx]
            home = parsed_teams[idx+1]
            
            # Skip misaligned iterations
            if away['role'] != 'Away' or home['role'] != 'Home':
                continue
                
            vegas_away_p = parse_odds_to_prob(away['odds'])
            vegas_home_p = parse_odds_to_prob(home['odds'])
            
            # P14 Expected Value Equation Margin Output
            away_ev = (away['win_p'] - vegas_away_p) * 100
            home_ev = (home['win_p'] - vegas_home_p) * 100

            print(f"\n⚾ MATCHUP: {away['name']} [Line: {away['odds']}] @ {home['name']} [Line: {home['odds']}]")
            print(f"  ↳ Away Model Proj: {away['win_p']:.2%} | Market Implied: {vegas_away_p:.2%} | Edge: {away_ev:+.2f}% EV")
            print(f"  ↳ Home Model Proj: {home['win_p']:.2%} | Market Implied: {vegas_home_p:.2%} | Edge: {home_ev:+.2f}% EV")
            
            # Print Actionable Edge Identifiers
            if away_ev >= 4.0:
                print(f"  🔥 STRATEGY ALERT: Heavy Value Spot on {away['name']} (Away)")
            if home_ev >= 4.0:
                print(f"  🔥 STRATEGY ALERT: Heavy Value Spot on {home['name']} (Home)")
        except:
            continue
            
    print("\n" + "="*75)

if __name__ == "__main__":
    parse_text_stream()
