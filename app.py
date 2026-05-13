import streamlit as st
import pandas as pd

# ============================================================
# DATA SYNC
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
        "🔄 Syncing with Google Sheets..."
    )

    st.stop()


# ============================================================
# MAIN
# ============================================================

try:

    # FIXED: reset index after removing blank rows
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

        "Vegas Odds":

            safe_get(
                main_df,
                "Vegas Away",
                4
            )

            + " / " +

            safe_get(
                main_df,
                "Vegas Home",
                5
            ),

        "Sharp ML %":

            safe_get(
                main_df,
                "Sharp ML Away",
                13
            )

            + " / " +

            safe_get(
                main_df,
                "Sharp ML Home",
                14
            ),

        "Sharp Dog":

            safe_get(
                main_df,
                "Sharp Dog",
                15
            ),

        "My Win %":

            safe_get(
                main_df,
                "My Win Away",
                18
            )

            + " / " +

            safe_get(
                main_df,
                "My Win Home",
                19
            ),

        "EV (A/H)":

            safe_get(
                main_df,
                "EV Away",
                22
            )

            + " / " +

            safe_get(
                main_df,
                "EV Home",
                23
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
    # METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Games",
        len(master_table)
    )

    c2.metric(
        "Sharp Targets",
        sharp_mask.sum()
    )

    c3.metric(
        "High EV Edges",
        high_ev_mask.sum()
    )

    c4.metric(
        "Market Status",
        "LIVE"
    )

    # ========================================================
    # TACTICAL BOARD
    # ========================================================

    st.subheader(
        "Tactical Board"
    )

    def highlight_logic(row):

        styles = [''] * len(row)

        if str(
            row["Sharp Dog"]
        ).strip():

            styles[3] = (
                "background-color:#d1e7ff;"
                "font-weight:bold"
            )

        if str(
            row["Model Pick"]
        ).strip():

            styles[6] = (
                "background-color:#c6efce;"
                "font-weight:bold"
            )

        return styles


    st.dataframe(

        master_table
        .style
        .apply(
            highlight_logic,
            axis=1
        ),

        use_container_width=True,
        height=700,
        hide_index=True
    )

    # ========================================================
    # DETAILED OUTLOOK
    # ========================================================

    st.divider()

    st.subheader(
        "📝 Detailed Tactical Outlook"
    )

    left, right = st.columns(2)

    # ========================================================
    # SHARP ALIGNMENT
    # ========================================================

    with left:

        st.markdown(
            "#### 🔥 Top Sharp Bets & Alignments"
        )

        for _, row in master_table.iterrows():

            sharp_team = normalize_team(
                row["Sharp Dog"]
            )

            if not sharp_team:

                continue

            model_pick = normalize_team(

                first_word(
                    row["Model Pick"]
                )
            )

            if (

                model_pick

                and

                sharp_team == model_pick

            ):

                st.success(

                    f"**ALIGNED**: "

                    f"{row['Matchup']} → "

                    f"Sharps + Model on "

                    f"**{sharp_team}**"
                )

            else:

                st.warning(

                    f"**SHARP BIAS**: "

                    f"{row['Matchup']} → "

                    f"Sharps on "

                    f"**{sharp_team}**"
                )

    # ========================================================
    # HIGH EV
    # ========================================================

    with right:

        st.markdown(
            "#### 📈 High EV Model Picks"
        )

        for idx in range(len(main_df)):

            if not high_ev_mask.iloc[idx]:

                continue

            row = master_table.iloc[idx]

            away_ev = to_n(
                ev_away.iloc[idx]
            )

            home_ev = to_n(
                ev_home.iloc[idx]
            )

            away_team = (
                row["Matchup"]
                .split("@")[0]
                .strip()
            )

            home_team = (
                row["Matchup"]
                .split("@")[1]
                .strip()
            )

            if (

                away_ev is not None

                and

                (
                    home_ev is None
                    or away_ev >= home_ev
                )

            ):

                edge_team = away_team
                edge_ev = away_ev

                vegas_line = safe_get(
                    main_df,
                    "Vegas Away",
                    4
                ).iloc[idx]

                win_pct = safe_get(
                    main_df,
                    "My Win Away",
                    18
                ).iloc[idx]

            else:

                edge_team = home_team
                edge_ev = home_ev

                vegas_line = safe_get(
                    main_df,
                    "Vegas Home",
                    5
                ).iloc[idx]

                win_pct = safe_get(
                    main_df,
                    "My Win Home",
                    19
                ).iloc[idx]

            # Grade
            if edge_ev >= 20:

                tier = "🟢 ELITE"

            elif edge_ev >= 15:

                tier = "🔵 STRONG"

            else:

                tier = "🟡 VALUE"

            sharp_team = normalize_team(
                row["Sharp Dog"]
            )

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

            signal = (

                "Sharps + Model"

                if aligned

                else "Model Only"

            )

            st.info(

                f"""
**{tier} EDGE** — {row['Matchup']}

**Model Pick:** {row['Model Pick']}  
**Edge Side:** {edge_team}  
**Expected Value:** {edge_ev:.2f}%  
**Vegas Line:** {vegas_line}  
**Model Win %:** {win_pct}  
**Signal:** {signal}
"""
            )

    # ========================================================
    # FIELD NOTES
    # ========================================================

    st.divider()

    st.subheader(
        "🔍 Individual Game Intel"
    )

    for _, row in master_table.iterrows():

        note = str(
            row["Tactical Note"]
        ).strip()

        if len(note) > 3:

            with st.expander(

                f"Field Note: "

                f"{row['Matchup']}"

            ):

                st.write(
                    note
                )


except Exception as e:

    st.error(
        f"Logic Error: {e}"
    )
