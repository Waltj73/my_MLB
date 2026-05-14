import streamlit as st
import pandas as pd

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MLB Command Center",
    layout="wide"
)

# ============================================================
# DATA
# ============================================================

SHEET_ID = "1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0"
GID = "0"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"


@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df.fillna("")
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()


# ============================================================
# HELPERS
# ============================================================

def to_n(v):
    try:
        return float(str(v).replace("%", "").replace(",", "").strip())
    except Exception:
        return None


def normalize_team(v):
    return str(v).strip().upper()


def first_word(v):
    parts = str(v).strip().split()
    return parts[0] if parts else ""


def safe_get(df, name_hint="", idx=None):
    if name_hint and name_hint in df.columns:
        return df[name_hint].astype(str)

    if idx is not None and idx < df.shape[1]:
        return df.iloc[:, idx].astype(str)

    return pd.Series([""] * len(df), index=df.index)


def edge_tier(ev):
    if ev is None:
        return "NO EDGE"
    if ev >= 20:
        return "🟢 ELITE EDGE"
    if ev >= 15:
        return "🔵 STRONG EDGE"
    if ev >= 10:
        return "🟡 VALUE EDGE"
    if ev >= 5:
        return "⚪ SMALL EDGE"
    return "NO EDGE"


def sharp_market_read(away_team, home_team, vegas_away, vegas_home, sharp_team):
    away_line = to_n(vegas_away)
    home_line = to_n(vegas_home)
    sharp_team_norm = normalize_team(sharp_team)

    if away_line is None or home_line is None or not sharp_team_norm:
        return "No clear sharp side is listed for this matchup."

    if away_line < home_line:
        favorite = normalize_team(away_team)
        dog = normalize_team(home_team)
        favorite_display = away_team
        dog_display = home_team
    else:
        favorite = normalize_team(home_team)
        dog = normalize_team(away_team)
        favorite_display = home_team
        dog_display = away_team

    if sharp_team_norm == dog:
        return (
            f"Sharps appear to be fading the Vegas favorite ({favorite_display}) "
            f"and taking the dog ({dog_display}). This usually points to price resistance, "
            f"favorite inflation, or hidden value on the plus-money side."
        )

    if sharp_team_norm == favorite:
        return (
            f"Sharps are backing the Vegas favorite ({favorite_display}). "
            f"This suggests respected money may still see value even at the favorite price."
        )

    return (
        "Sharp side does not clearly match the listed favorite or underdog. "
        "Check team naming in the sheet."
    )


def ev_side(row):
    away_ev = row["EV Away"]
    home_ev = row["EV Home"]

    away_ev = away_ev if pd.notna(away_ev) else -999
    home_ev = home_ev if pd.notna(home_ev) else -999

    if away_ev >= home_ev:
        return row["Away Team"], row["Vegas Away"], row["My Win Away"], row["EV Away"], "away"

    return row["Home Team"], row["Vegas Home"], row["My Win Home"], row["EV Home"], "home"


def model_pick_team(model_pick):
    return normalize_team(first_word(model_pick))


# ============================================================
# WRITEUP HELPERS
# ============================================================

def write_sharp_card(row):
    sharp_team = normalize_team(row["Sharp Dog"])
    model_team = model_pick_team(row["Model Pick"])

    aligned = sharp_team and model_team and sharp_team == model_team

    away_ev = row["EV Away"]
    home_ev = row["EV Home"]

    best_ev = max(
        away_ev if pd.notna(away_ev) else -999,
        home_ev if pd.notna(home_ev) else -999
    )

    market_read = sharp_market_read(
        row["Away Team"],
        row["Home Team"],
        row["Vegas Away"],
        row["Vegas Home"],
        row["Sharp Dog"]
    )

    if aligned:
        confirmation = "Sharps and model are aligned."
        interpretation = (
            "This is the cleaner type of sharp setup because the sharp side and your model pick "
            "are pointing to the same team. That does not guarantee a win, but it does give the play "
            "more confirmation than a sharp-only signal."
        )
    else:
        confirmation = "Sharp side lacks model confirmation."
        interpretation = (
            "This is not an automatic bet. Sharps appear interested, but your model is not fully confirming "
            "the same side. Treat this as a watchlist game or reduce confidence unless another factor supports it."
        )

    return f"""
### 🔥 Sharp Money Read — {row['Matchup']}

**Sharp Side:** {sharp_team if sharp_team else "NONE"}  
**Model Pick:** {row['Model Pick'] if str(row['Model Pick']).strip() else "NO PICK"}  
**Confirmation:** {confirmation}

---

### Market Read

{market_read}

---

### Vegas Lines

- **{row['Away Team']}**: {row['Vegas Away']}
- **{row['Home Team']}**: {row['Vegas Home']}

### Sharp ML

- **{row['Away Team']}**: {row['Sharp ML Away']}
- **{row['Home Team']}**: {row['Sharp ML Home']}

### My Win %

- **{row['Away Team']}**: {row['My Win Away']}
- **{row['Home Team']}**: {row['My Win Home']}

### EV

- **{row['Away Team']}**: {row['EV Away']:.2f}%
- **{row['Home Team']}**: {row['EV Home']:.2f}%

---

### Betting Interpretation

{interpretation}

**Tier:** {edge_tier(best_ev)}
"""


def write_ev_card(row):
    edge_team, edge_line, edge_win, edge_ev, side = ev_side(row)

    sharp_team = normalize_team(row["Sharp Dog"])
    model_team = model_pick_team(row["Model Pick"])
    edge_team_norm = normalize_team(edge_team)

    sharp_confirmed = sharp_team and sharp_team == edge_team_norm
    model_confirmed = model_team and model_team == edge_team_norm

    market_read = sharp_market_read(
        row["Away Team"],
        row["Home Team"],
        row["Vegas Away"],
        row["Vegas Home"],
        row["Sharp Dog"]
    )

    if sharp_confirmed and model_confirmed:
        confirmation = "Sharps, model pick, and EV all align."
        interpretation = (
            "This is the strongest type of betting signal in your sheet. The model sees value, "
            "the pick agrees with the EV side, and the sharp side is also pointing in the same direction."
        )
    elif model_confirmed:
        confirmation = "Model agrees with EV, but sharp confirmation is missing."
        interpretation = (
            "This is still a valid model play. The edge comes from your numbers, not necessarily sharp money. "
            "This type of play can be useful, but it should not be sized as aggressively as a full confluence play."
        )
    elif sharp_confirmed:
        confirmation = "Sharps agree with EV, but the model pick may differ."
        interpretation = (
            "This is an interesting market-backed value spot, but the model pick conflict lowers confidence. "
            "Treat this as a lean unless you have additional matchup reasons to support it."
        )
    else:
        confirmation = "EV exists with limited confirmation."
        interpretation = (
            "There is value showing, but it lacks confirmation from either the model pick or sharp side. "
            "This is lower confidence and should not be forced."
        )

    return f"""
### 📈 {edge_tier(edge_ev)} — {row['Matchup']}

**Edge Side:** {edge_team}  
**Vegas Line:** {edge_line}  
**My Win %:** {edge_win}  
**Expected Value:** {edge_ev:.2f}%

---

### Why This Matters

The model is showing that **{edge_team}** is priced better than the sportsbook line suggests.  
The value is not simply about who is more likely to win — it is about whether the market price is wrong.

---

### Confirmation Check

**Model Pick:** {row['Model Pick'] if str(row['Model Pick']).strip() else "NO PICK"}  
**Sharp Side:** {sharp_team if sharp_team else "NONE"}  
**Read:** {confirmation}

---

### Market Read

{market_read}

---

### Full Breakdown

**{row['Away Team']}**

- Vegas: {row['Vegas Away']}
- My Win %: {row['My Win Away']}
- EV: {row['EV Away']:.2f}%

**{row['Home Team']}**

- Vegas: {row['Vegas Home']}
- My Win %: {row['My Win Home']}
- EV: {row['EV Home']:.2f}%

---

### Betting Interpretation

{interpretation}
"""


def write_signal_card(row):
    sharp_team = normalize_team(row["Sharp Dog"])
    model_team = model_pick_team(row["Model Pick"])

    away_ev = row["EV Away"]
    home_ev = row["EV Home"]

    best_ev = max(
        away_ev if pd.notna(away_ev) else -999,
        home_ev if pd.notna(home_ev) else -999
    )

    market_read = sharp_market_read(
        row["Away Team"],
        row["Home Team"],
        row["Vegas Away"],
        row["Vegas Home"],
        row["Sharp Dog"]
    )

    return f"""
### 🎯 {edge_tier(best_ev)} SIGNAL — {row['Matchup']}

**Play Side:** {model_team}  
**Model Pick:** {row['Model Pick']}  
**Sharp Side:** {sharp_team}

---

### Why This Is a Signal

This is a confluence play because sharp side, model pick, and positive EV are all present.

That does not make it a lock, but it does mean multiple parts of your board are pointing in the same direction.

---

### Vegas Lines

- **{row['Away Team']}**: {row['Vegas Away']}
- **{row['Home Team']}**: {row['Vegas Home']}

### My Win %

- **{row['Away Team']}**: {row['My Win Away']}
- **{row['Home Team']}**: {row['My Win Home']}

### EV

- **{row['Away Team']}**: {row['EV Away']:.2f}%
- **{row['Home Team']}**: {row['EV Home']:.2f}%

---

### Market Read

{market_read}

---

### Betting Interpretation

This is the type of play to consider before lower-confidence spots because it combines model edge with market behavior.

Still, MLB variance is high. Treat this as a qualified edge, not a guaranteed outcome.
"""


# ============================================================
# UI
# ============================================================

st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if df.empty:
    st.info("🔄 Syncing...")
    st.stop()


# ============================================================
# MAIN
# ============================================================

try:
    main_df = df[
        df.iloc[:, 0].astype(str).str.len() > 2
    ].copy().reset_index(drop=True)

    away_team = safe_get(main_df, "Away Team", 0)
    home_team = safe_get(main_df, "Home Team", 1)

    vegas_away = safe_get(main_df, "Vegas Away", 4)
    vegas_home = safe_get(main_df, "Vegas Home", 5)

    sharp_ml_away = safe_get(main_df, "Sharp ML Away", 13)
    sharp_ml_home = safe_get(main_df, "Sharp ML Home", 14)

    sharp_dog = safe_get(main_df, "Sharp Dog", 15)

    win_away = safe_get(main_df, "My Win Away", 18)
    win_home = safe_get(main_df, "My Win Home", 19)

    ev_away = pd.to_numeric(
        safe_get(main_df, "EV Away", 22),
        errors="coerce"
    )

    ev_home = pd.to_numeric(
        safe_get(main_df, "EV Home", 23),
        errors="coerce"
    )

    pick_team = safe_get(main_df, "Pick Team", 25)
    pick_side = safe_get(main_df, "Pick Side", 26)

    master_table = pd.DataFrame({
        "Matchup": away_team + " @ " + home_team,
        "Away Team": away_team,
        "Home Team": home_team,
        "Vegas Away": vegas_away,
        "Vegas Home": vegas_home,
        "Sharp ML Away": sharp_ml_away,
        "Sharp ML Home": sharp_ml_home,
        "Sharp Dog": sharp_dog,
        "My Win Away": win_away,
        "My Win Home": win_home,
        "EV Away": ev_away,
        "EV Home": ev_home,
        "Model Pick": pick_team + " " + pick_side,
    })

    high_ev_mask = (
        (master_table["EV Away"] > 10) |
        (master_table["EV Home"] > 10)
    )

    sharp_mask = (
        master_table["Sharp Dog"]
        .astype(str)
        .str.strip()
        .str.len() > 1
    )

    signal_count = 0

    for idx, row in master_table.iterrows():
        sharp_team = normalize_team(row["Sharp Dog"])
        model_team = normalize_team(first_word(row["Model Pick"]))

        if sharp_team and model_team and sharp_team == model_team and high_ev_mask.iloc[idx]:
            signal_count += 1

    # ========================================================
    # METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Games", len(master_table))
    c2.metric("Sharp Targets", int(sharp_mask.sum()))
    c3.metric("High EV", int(high_ev_mask.sum()))
    c4.metric("Signal Plays", signal_count)

    # ========================================================
    # TABS
    # ========================================================

    board_tab, sharp_tab, ev_tab, signal_tab = st.tabs([
        "📋 Tactical Board",
        "🔥 Sharp Money",
        "📈 High EV",
        "🎯 Signal Plays"
    ])

    # ========================================================
    # BOARD TAB
    # ========================================================

    with board_tab:
        st.subheader("📋 Full Tactical Board")

        board_view = master_table[[
            "Matchup",
            "Vegas Away",
            "Vegas Home",
            "Sharp ML Away",
            "Sharp ML Home",
            "Sharp Dog",
            "My Win Away",
            "My Win Home",
            "EV Away",
            "EV Home",
            "Model Pick"
        ]]

        def style_tactical_board(row):
            styles = [''] * len(row)

            sharp_dog_norm = normalize_team(row["Sharp Dog"])
            model_team_norm = normalize_team(first_word(row["Model Pick"]))

            ev_a = to_n(row["EV Away"])
            ev_h = to_n(row["EV Home"])

            high_ev = (
                (ev_a is not None and ev_a > 10) or
                (ev_h is not None and ev_h > 10)
            )

            aligned = (
                sharp_dog_norm and
                model_team_norm and
                sharp_dog_norm == model_team_norm
            )

            col_map = {
                "Sharp Dog": 5,
                "EV Away": 8,
                "EV Home": 9,
                "Model Pick": 10
            }

            if sharp_dog_norm:
                styles[col_map["Sharp Dog"]] = (
                    "background-color:#d1e7ff;"
                    "color:#004085;"
                    "font-weight:bold;"
                )

            if model_team_norm:
                styles[col_map["Model Pick"]] = (
                    "background-color:#c6efce;"
                    "color:#006100;"
                    "font-weight:bold;"
                )

            if ev_a is not None and ev_a > 10:
                styles[col_map["EV Away"]] = (
                    "background-color:#fff3cd;"
                    "color:#856404;"
                    "font-weight:bold;"
                )

            if ev_h is not None and ev_h > 10:
                styles[col_map["EV Home"]] = (
                    "background-color:#fff3cd;"
                    "color:#856404;"
                    "font-weight:bold;"
                )

            if aligned and high_ev:
                styles = [
                    "background-color:#d4edda;"
                    "color:#155724;"
                    "font-weight:bold;"
                ] * len(row)

            return styles

        st.dataframe(
            board_view.style.apply(style_tactical_board, axis=1),
            use_container_width=True,
            hide_index=True,
            height=700
        )

    # ========================================================
    # SHARP TAB
    # ========================================================

    with sharp_tab:
        st.subheader("🔥 Sharp Money Targets")

        sharp_rows = master_table[sharp_mask]

        if sharp_rows.empty:
            st.warning("No sharp money targets found.")

        for idx, row in sharp_rows.iterrows():
            sharp_team = normalize_team(row["Sharp Dog"])
            model_team = normalize_team(first_word(row["Model Pick"]))

            aligned = sharp_team and model_team and sharp_team == model_team

            if aligned:
                st.success(write_sharp_card(row))
            else:
                st.warning(write_sharp_card(row))

    # ========================================================
    # EV TAB
    # ========================================================

    with ev_tab:
        st.subheader("📈 High EV Model Plays")

        ev_rows = master_table[high_ev_mask]

        if ev_rows.empty:
            st.warning("No high EV plays found.")

        for idx, row in ev_rows.iterrows():
            edge_team, edge_line, edge_win, edge_ev, side = ev_side(row)

            sharp_team = normalize_team(row["Sharp Dog"])
            model_team = normalize_team(first_word(row["Model Pick"]))
            edge_team_norm = normalize_team(edge_team)

            sharp_confirmed = sharp_team and sharp_team == edge_team_norm
            model_confirmed = model_team and model_team == edge_team_norm

            if sharp_confirmed and model_confirmed:
                st.success(write_ev_card(row))
            elif model_confirmed:
                st.info(write_ev_card(row))
            else:
                st.warning(write_ev_card(row))

    # ========================================================
    # SIGNAL TAB
    # ========================================================

    with signal_tab:
        st.subheader("🎯 Signal Plays")

        found_signal = False

        for idx, row in master_table.iterrows():
            if not high_ev_mask.iloc[idx]:
                continue

            sharp_team = normalize_team(row["Sharp Dog"])
            model_team = normalize_team(first_word(row["Model Pick"]))

            if not sharp_team or not model_team:
                continue

            if sharp_team != model_team:
                continue

            found_signal = True
            st.success(write_signal_card(row))

        if not found_signal:
            st.warning("No signal plays found.")

except Exception as e:
    st.error(f"Logic Error: {e}")
