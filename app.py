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

EV_THRESHOLD = 5
DIFF_THRESHOLD = 5
HIGH_EV_THRESHOLD = 10


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
        return float(str(v).replace("%", "").replace(",", "").replace("+", "").strip())
    except Exception:
        return None


def normalize_team(v):
    return str(v).strip().upper()


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
        favorite_display = away_team
        dog_display = home_team
    else:
        favorite_display = home_team
        dog_display = away_team

    if sharp_team_norm == normalize_team(dog_display):
        return (
            f"Sharps appear to be fading the Vegas favorite ({favorite_display}) "
            f"and taking the dog ({dog_display})."
        )

    if sharp_team_norm == normalize_team(favorite_display):
        return (
            f"Sharps are backing the Vegas favorite ({favorite_display})."
        )

    return "Sharp side does not clearly match the listed favorite or underdog."


def calculate_model_pick(row):
    away_ev = row["EV Away"]
    home_ev = row["EV Home"]

    away_diff = to_n(row["Diff Away"])
    home_diff = to_n(row["Diff Home"])

    away_ev_ok = pd.notna(away_ev) and away_ev > EV_THRESHOLD and away_diff is not None and away_diff >= DIFF_THRESHOLD
    home_ev_ok = pd.notna(home_ev) and home_ev > EV_THRESHOLD and home_diff is not None and home_diff >= DIFF_THRESHOLD

    if away_ev_ok and (not home_ev_ok or away_ev >= home_ev):
        return row["Away Team"], "Away", away_ev, away_diff

    if home_ev_ok and (not away_ev_ok or home_ev > away_ev):
        return row["Home Team"], "Home", home_ev, home_diff

    return "PASS", "Pass", max(
        away_ev if pd.notna(away_ev) else -999,
        home_ev if pd.notna(home_ev) else -999
    ), max(
        away_diff if away_diff is not None else -999,
        home_diff if home_diff is not None else -999
    )


# ============================================================
# WRITEUPS
# ============================================================

def write_ev_card(row):
    pick = row["Model Pick"]

    if pick == "PASS":
        return f"""
### {row['Matchup']}

**PASS**

No clean model edge based on EV and Diff thresholds.
"""

    sharp_team = normalize_team(row["Sharp Dog"])
    pick_norm = normalize_team(pick)

    if sharp_team and sharp_team == pick_norm:
        sharp_read = "Sharp side and model pick are aligned."
    elif sharp_team:
        sharp_read = f"Sharp side points to {row['Sharp Dog']}, while the model points to {pick}. This is a conflict."
    else:
        sharp_read = "No sharp dog signal listed."

    market_read = sharp_market_read(
        row["Away Team"],
        row["Home Team"],
        row["Vegas Away"],
        row["Vegas Home"],
        row["Sharp Dog"]
    )

    return f"""
### 📈 {edge_tier(row['Pick EV'])} — {row['Matchup']}

**Model Pick:** {pick}  
**Side:** {row['Pick Side']}  
**EV:** {row['Pick EV']:.2f}%  
**Diff:** {row['Pick Diff']:.2f}%

---

### Why This Is a Play

Your model is showing that **{pick}** has enough value to qualify based on your rules:

- EV greater than {EV_THRESHOLD}
- Difference greater than or equal to {DIFF_THRESHOLD}

---

### Market Read

{market_read}

---

### Sharp Confirmation

{sharp_read}

---

### Full Breakdown

**{row['Away Team']}**

- Vegas: {row['Vegas Away']}
- My Win %: {row['My Win Away']}
- Diff: {row['Diff Away']}
- EV: {row['EV Away']:.2f}%

**{row['Home Team']}**

- Vegas: {row['Vegas Home']}
- My Win %: {row['My Win Home']}
- Diff: {row['Diff Home']}
- EV: {row['EV Home']:.2f}%

---

### Interpretation

This is a valid model play because the qualifying side is the same side carrying the positive EV and positive edge.
"""


def write_signal_card(row):
    return f"""
### 🎯 SIGNAL PLAY — {row['Matchup']}

**Play Side:** {row['Model Pick']}  
**Sharp Side:** {row['Sharp Dog']}  
**EV:** {row['Pick EV']:.2f}%  
**Diff:** {row['Pick Diff']:.2f}%

---

### Why This Is a Signal

This qualifies because all three are pointing to the same team:

- Model Pick
- Sharp Dog
- Positive EV / positive Diff

This is your cleanest type of setup.
"""


def write_sharp_card(row):
    sharp_team = row["Sharp Dog"]
    pick = row["Model Pick"]

    sharp_norm = normalize_team(sharp_team)
    pick_norm = normalize_team(pick)

    aligned = sharp_norm and pick_norm and sharp_norm == pick_norm

    if aligned:
        read = "Sharps and model are aligned."
    else:
        read = "Sharps and model are not aligned."

    return f"""
### 🔥 Sharp Money — {row['Matchup']}

**Sharp Side:** {sharp_team if sharp_team else "NONE"}  
**Model Pick:** {pick}  
**Read:** {read}

---

### Sharp ML

- {row['Away Team']}: {row['Sharp ML Away']}
- {row['Home Team']}: {row['Sharp ML Home']}

---

### Betting Interpretation

If sharp side and model pick align, confidence improves.  
If they conflict, this is a caution game, not a signal.
"""


# ============================================================
# LOAD SHEET
# ============================================================

st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if df.empty:
    st.info("🔄 Syncing...")
    st.stop()


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

    diff_away = safe_get(main_df, "Diff Away", 20)
    diff_home = safe_get(main_df, "Diff Home", 21)

    ev_away = pd.to_numeric(safe_get(main_df, "EV Away", 22), errors="coerce")
    ev_home = pd.to_numeric(safe_get(main_df, "EV Home", 23), errors="coerce")

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
        "Diff Away": diff_away,
        "Diff Home": diff_home,
        "EV Away": ev_away,
        "EV Home": ev_home,
    })

    picks = master_table.apply(calculate_model_pick, axis=1)

    master_table["Model Pick"] = [p[0] for p in picks]
    master_table["Pick Side"] = [p[1] for p in picks]
    master_table["Pick EV"] = [p[2] for p in picks]
    master_table["Pick Diff"] = [p[3] for p in picks]

    high_ev_mask = master_table["Model Pick"] != "PASS"

    sharp_mask = (
        master_table["Sharp Dog"]
        .astype(str)
        .str.strip()
        .str.len() > 1
    )

    signal_mask = master_table.apply(
        lambda row: (
            row["Model Pick"] != "PASS"
            and normalize_team(row["Model Pick"]) == normalize_team(row["Sharp Dog"])
            and row["Pick EV"] > HIGH_EV_THRESHOLD
            and row["Pick Diff"] >= DIFF_THRESHOLD
        ),
        axis=1
    )

    # ========================================================
    # METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Games", len(master_table))
    c2.metric("Sharp Targets", int(sharp_mask.sum()))
    c3.metric("Model Plays", int(high_ev_mask.sum()))
    c4.metric("Signal Plays", int(signal_mask.sum()))

    # ========================================================
    # TABS
    # ========================================================

    board_tab, sharp_tab, ev_tab, signal_tab = st.tabs([
        "📋 Tactical Board",
        "🔥 Sharp Money",
        "📈 Model Plays",
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
            "Diff Away",
            "Diff Home",
            "EV Away",
            "EV Home",
            "Model Pick",
            "Pick EV",
            "Pick Diff"
        ]]

        def style_tactical_board(row):
            styles = [''] * len(row)

            col_map = {name: idx for idx, name in enumerate(row.index)}

            if row["Model Pick"] != "PASS":
                styles[col_map["Model Pick"]] = (
                    "background-color:#c6efce;color:#006100;font-weight:bold;"
                )

            if row["Sharp Dog"]:
                styles[col_map["Sharp Dog"]] = (
                    "background-color:#d1e7ff;color:#004085;font-weight:bold;"
                )

            for col in ["EV Away", "EV Home", "Pick EV"]:
                val = to_n(row[col])
                if val is not None and val > 10:
                    styles[col_map[col]] = (
                        "background-color:#fff3cd;color:#856404;font-weight:bold;"
                    )

            if (
                row["Model Pick"] != "PASS"
                and normalize_team(row["Model Pick"]) == normalize_team(row["Sharp Dog"])
                and row["Pick EV"] > HIGH_EV_THRESHOLD
            ):
                styles = [
                    "background-color:#d4edda;color:#155724;font-weight:bold;"
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

        for _, row in sharp_rows.iterrows():
            if normalize_team(row["Sharp Dog"]) == normalize_team(row["Model Pick"]):
                st.success(write_sharp_card(row))
            else:
                st.warning(write_sharp_card(row))

    # ========================================================
    # MODEL PLAY TAB
    # ========================================================

    with ev_tab:
        st.subheader("📈 Model Plays")

        model_rows = master_table[high_ev_mask].sort_values(
            by="Pick EV",
            ascending=False
        )

        if model_rows.empty:
            st.warning("No model plays found.")

        for _, row in model_rows.iterrows():
            st.info(write_ev_card(row))

    # ========================================================
    # SIGNAL TAB
    # ========================================================

    with signal_tab:
        st.subheader("🎯 Signal Plays")

        signal_rows = master_table[signal_mask].sort_values(
            by="Pick EV",
            ascending=False
        )

        if signal_rows.empty:
            st.warning("No signal plays found.")

        for _, row in signal_rows.iterrows():
            st.success(write_signal_card(row))

except Exception as e:
    st.error(f"Logic Error: {e}")
