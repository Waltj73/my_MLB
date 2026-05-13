import streamlit as st
import pandas as pd

# ============================================================
# DATA
# ============================================================

SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0'

URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'


@st.cache_data(ttl=15)
def load_data():
    try:
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df.fillna('')
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()


# ============================================================
# HELPERS
# ============================================================

def to_n(v):
    try:
        return float(str(v).replace('%', '').replace(',', '').strip())
    except:
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

    return "LOW EDGE"


# ============================================================
# UI
# ============================================================

st.set_page_config(
    page_title="MLB Command Center",
    layout="wide"
)

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
    notes = safe_get(main_df, "Tactical Note", 27)

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
        "Tactical Note": notes
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
    # TOP METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Games", len(master_table))
    c2.metric("Sharp Targets", int(sharp_mask.sum()))
    c3.metric("High EV", int(high_ev_mask.sum()))
    c4.metric("Signal Plays", signal_count)

    # ========================================================
    # TABS
    # ========================================================

    board_tab, sharp_tab, ev_tab, signal_tab, notes_tab = st.tabs([
        "📋 Tactical Board",
        "🔥 Sharp Money",
        "📈 High EV",
        "🎯 Signal Plays",
        "🔍 Field Notes"
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

        st.dataframe(
            board_view,
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

            aligned = (
                sharp_team and model_team and sharp_team == model_team
            )

            away_ev = row["EV Away"]
            home_ev = row["EV Home"]

            best_ev = max(
                away_ev if pd.notna(away_ev) else -999,
                home_ev if pd.notna(home_ev) else -999
            )

            if aligned:
                box = st.success
                signal = "Sharps and model are aligned."
            else:
                box = st.warning
                signal = "Sharp side is not confirmed by the model."

            box(
                f"""
### {row['Matchup']}

**Sharp Side:** {sharp_team}  
**Model Pick:** {row['Model Pick'] if str(row['Model Pick']).strip() else 'NO PICK'}  
**Signal Read:** {signal}

**Vegas Lines:** {row['Away Team']} {row['Vegas Away']} / {row['Home Team']} {row['Vegas Home']}  
**Sharp ML %:** {row['Away Team']} {row['Sharp ML Away']} / {row['Home Team']} {row['Sharp ML Home']}  
**My Win %:** {row['Away Team']} {row['My Win Away']} / {row['Home Team']} {row['My Win Home']}  
**EV:** {row['Away Team']} {row['EV Away']:.2f}% / {row['Home Team']} {row['EV Home']:.2f}%  
**Best EV Tier:** {edge_tier(best_ev)}
"""
            )

    # ========================================================
    # EV TAB
    # ========================================================

    with ev_tab:

        st.subheader("📈 High EV Model Plays")

        ev_rows = master_table[high_ev_mask]

        if ev_rows.empty:

            st.warning("No high EV model plays found.")

        for idx, row in ev_rows.iterrows():

            away_ev = row["EV Away"]
            home_ev = row["EV Home"]

            if pd.notna(away_ev) and (
                pd.isna(home_ev) or away_ev >= home_ev
            ):
                edge_team = row["Away Team"]
                edge_ev = away_ev
                edge_line = row["Vegas Away"]
                edge_win = row["My Win Away"]
            else:
                edge_team = row["Home Team"]
                edge_ev = home_ev
                edge_line = row["Vegas Home"]
                edge_win = row["My Win Home"]

            sharp_team = normalize_team(row["Sharp Dog"])
            model_team = normalize_team(first_word(row["Model Pick"]))

            sharp_confirmed = (
                sharp_team and sharp_team == normalize_team(edge_team)
            )

            model_confirmed = (
                model_team and model_team == normalize_team(edge_team)
            )

            if sharp_confirmed and model_confirmed:
                confirmation = "Model edge, model pick, and sharp side all agree."
                box = st.success
            elif model_confirmed:
                confirmation = "Model edge agrees with the model pick, but sharp confirmation is missing."
                box = st.info
            elif sharp_confirmed:
                confirmation = "Sharp side agrees with the EV edge, but the model pick may differ."
                box = st.warning
            else:
                confirmation = "EV edge exists, but confirmation is limited."
                box = st.warning

            box(
                f"""
### {edge_tier(edge_ev)} — {row['Matchup']}

**Edge Side:** {edge_team}  
**Expected Value:** {edge_ev:.2f}%  
**Vegas Line:** {edge_line}  
**My Win %:** {edge_win}  
**Model Pick:** {row['Model Pick'] if str(row['Model Pick']).strip() else 'NO PICK'}  
**Sharp Side:** {sharp_team if sharp_team else 'NO SHARP DOG'}

**Full Game View:**  
{row['Away Team']} — Vegas {row['Vegas Away']} | My Win {row['My Win Away']} | EV {row['EV Away']:.2f}%  
{row['Home Team']} — Vegas {row['Vegas Home']} | My Win {row['My Win Home']} | EV {row['EV Home']:.2f}%

**Analysis:** {confirmation}
"""
            )

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

            away_ev = row["EV Away"]
            home_ev = row["EV Home"]

            best_ev = max(
                away_ev if pd.notna(away_ev) else -999,
                home_ev if pd.notna(home_ev) else -999
            )

            st.success(
                f"""
### 🎯 {edge_tier(best_ev)} SIGNAL — {row['Matchup']}

**Play Side:** {model_team}  
**Model Pick:** {row['Model Pick']}  
**Sharp Side:** {sharp_team}  
**Vegas Lines:** {row['Away Team']} {row['Vegas Away']} / {row['Home Team']} {row['Vegas Home']}  
**My Win %:** {row['Away Team']} {row['My Win Away']} / {row['Home Team']} {row['My Win Home']}  
**EV:** {row['Away Team']} {row['EV Away']:.2f}% / {row['Home Team']} {row['EV Home']:.2f}%  

**Read:** This is a confluence play because sharp money, model direction, and positive EV are all present.
"""
            )

        if not found_signal:
            st.warning("No signal plays found.")

    # ========================================================
    # NOTES TAB
    # ========================================================

    with notes_tab:

        st.subheader("🔍 Field Notes")

        for _, row in master_table.iterrows():

            note = str(row["Tactical Note"]).strip()

            if len(note) > 3:

                with st.expander(f"{row['Matchup']}"):

                    st.write(note)

except Exception as e:

    st.error(f"Logic Error: {e}")
