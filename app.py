import streamlit as st
import pandas as pd

# ============================================================
# DATA
# ============================================================

SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0'

URL = (
    f'https://docs.google.com/spreadsheets/d/'
    f'{SHEET_ID}/export?format=csv&gid={GID}'
)


@st.cache_data(ttl=15)
def load_data():

    try:

        df = pd.read_csv(
            URL,
            skiprows=1
        )

        df.columns = [
            str(c).strip()
            for c in df.columns
        ]

        return df.fillna('')

    except Exception as e:

        st.error(
            f"Sync Error: {e}"
        )

        return pd.DataFrame()


# ============================================================
# HELPERS
# ============================================================

def to_n(v):

    try:

        return float(
            str(v)
            .replace('%', '')
            .replace(',', '')
            .strip()
        )

    except:

        return None


def normalize_team(v):

    return (
        str(v)
        .strip()
        .upper()
    )


def first_word(v):

    parts = (
        str(v)
        .strip()
        .split()
    )

    return (
        parts[0]
        if parts
        else ""
    )


def safe_get(df, name_hint="", idx=None):

    if (
        name_hint
        and name_hint in df.columns
    ):

        return (
            df[name_hint]
            .astype(str)
        )

    if (
        idx is not None
        and idx < df.shape[1]
    ):

        return (
            df.iloc[:, idx]
            .astype(str)
        )

    return pd.Series(
        [""] * len(df),
        index=df.index
    )


# ============================================================
# UI
# ============================================================

st.set_page_config(
    page_title="MLB Command Center",
    layout="wide"
)

st.title(
    "⚾ 2026 MLB Tactical Command Center"
)

df = load_data()

if df.empty:

    st.info(
        "🔄 Syncing..."
    )

    st.stop()


# ============================================================
# MAIN
# ============================================================

try:

    main_df = df[
        df.iloc[:, 0]
        .astype(str)
        .str.len() > 2
    ].copy().reset_index(drop=True)

    # ========================================================
    # MASTER TABLE
    # ========================================================

    master_table = pd.DataFrame({

        "Matchup":

            safe_get(
                main_df,
                "Away Team",
                0
            )

            + " @ " +

            safe_get(
                main_df,
                "Home Team",
                1
            ),

        "Sharp Dog":

            safe_get(
                main_df,
                "Sharp Dog",
                15
            ),

        "Model Pick":

            safe_get(
                main_df,
                "Pick Team",
                25
            )

            + " " +

            safe_get(
                main_df,
                "Pick Side",
                26
            ),

        "Tactical Note":

            safe_get(
                main_df,
                "Tactical Note",
                27
            )
    })

    # ========================================================
    # EV
    # ========================================================

    ev_away = pd.to_numeric(

        safe_get(
            main_df,
            "EV Away",
            22
        ),

        errors="coerce"
    )

    ev_home = pd.to_numeric(

        safe_get(
            main_df,
            "EV Home",
            23
        ),

        errors="coerce"
    )

    high_ev_mask = (

        (ev_away > 10)

        |

        (ev_home > 10)

    )

    sharp_mask = (

        master_table["Sharp Dog"]

        .astype(str)

        .str.strip()

        .str.len() > 1
    )

    # ========================================================
    # TOP METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Games",
        len(master_table)
    )

    c2.metric(
        "Sharp Targets",
        sharp_mask.sum()
    )

    c3.metric(
        "High EV",
        high_ev_mask.sum()
    )

    c4.metric(
        "Market",
        "LIVE"
    )

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
    # BOARD
    # ========================================================

    with board_tab:

        st.dataframe(
            master_table,
            use_container_width=True,
            hide_index=True,
            height=700
        )

    # ========================================================
    # SHARP TAB
    # ========================================================

    with sharp_tab:

        st.subheader(
            "🔥 Sharp Money Targets"
        )

        for idx, row in master_table.iterrows():

            sharp_team = normalize_team(
                row["Sharp Dog"]
            )

            if not sharp_team:

                continue

            model_team = normalize_team(
                first_word(
                    row["Model Pick"]
                )
            )

            aligned = (
                sharp_team
                and
                sharp_team == model_team
            )

            if aligned:

                st.success(

                    f"{row['Matchup']} → "

                    f"{sharp_team} "

                    f"(Sharps + Model)"
                )

            else:

                st.warning(

                    f"{row['Matchup']} → "

                    f"{sharp_team} "

                    f"(Sharp Only)"
                )

    # ========================================================
    # EV TAB
    # ========================================================

    with ev_tab:

        st.subheader(
            "📈 High EV Model Plays"
        )

        for idx in range(
            len(main_df)
        ):

            if not high_ev_mask.iloc[idx]:

                continue

            row = master_table.iloc[idx]

            away_ev = to_n(
                ev_away.iloc[idx]
            )

            home_ev = to_n(
                ev_home.iloc[idx]
            )

            edge_ev = max(
                away_ev or -999,
                home_ev or -999
            )

            if edge_ev >= 20:

                tier = "🟢 ELITE"

            elif edge_ev >= 15:

                tier = "🔵 STRONG"

            else:

                tier = "🟡 VALUE"

            st.info(

                f"{tier} → "

                f"{row['Matchup']} "

                f"({edge_ev:.2f}%)"
            )

    # ========================================================
    # SIGNAL TAB
    # ========================================================

    with signal_tab:

        st.subheader(
            "🎯 Signal Plays"
        )

        signal_found = False

        for idx in range(
            len(main_df)
        ):

            if not high_ev_mask.iloc[idx]:

                continue

            row = master_table.iloc[idx]

            sharp_team = normalize_team(
                row["Sharp Dog"]
            )

            model_team = normalize_team(
                first_word(
                    row["Model Pick"]
                )
            )

            if (

                sharp_team

                and

                sharp_team == model_team

            ):

                signal_found = True

                edge_ev = max(

                    to_n(
                        ev_away.iloc[idx]
                    ) or -999,

                    to_n(
                        ev_home.iloc[idx]
                    ) or -999

                )

                if edge_ev >= 20:

                    st.success(

                        f"🟢 ELITE SIGNAL → "

                        f"{row['Matchup']} "

                        f"→ {model_team} "

                        f"({edge_ev:.2f}%)"
                    )

                else:

                    st.info(

                        f"🎯 SIGNAL → "

                        f"{row['Matchup']} "

                        f"→ {model_team} "

                        f"({edge_ev:.2f}%)"
                    )

        if not signal_found:

            st.warning(
                "No signal plays found."
            )

    # ========================================================
    # NOTES
    # ========================================================

    with notes_tab:

        for _, row in master_table.iterrows():

            note = str(
                row["Tactical Note"]
            ).strip()

            if len(note) > 3:

                with st.expander(

                    f"{row['Matchup']}"

                ):

                    st.write(
                        note
                    )


except Exception as e:

    st.error(
        f"Logic Error: {e}"
    )
