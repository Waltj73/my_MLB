import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Locked to "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' # GID for the first tab ("Model")
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Skips Row 1 to align with Away/Home headers
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI CONFIG ---
st.set_page_config(page_title="MLB Command Center", layout="wide")
st.title("⚾ 2026 MLB Tactical Command Center")

df = load_data()

if not df.empty:
    try:
        # Filter for active game rows
        main_df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0] != '0')].copy()

        # Helper for numeric cleaning
        def to_n(v): return pd.to_numeric(str(v).replace('%','').strip(), errors='coerce')

        # --- 3. THE MASTER DATA TABLE ---
        # Mapping based on image_1f6ff9.png
        # Vegas(4,5) | SharpML(13,14) | SharpDog(15) | MyWin(18,19) | Diff(20,21) | EV(22,23) | Picks(25,26)
        master_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "Sharp ML %": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Dog": main_df.iloc[:, 15].fillna('—'),
            "My Win %": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (A/H)": main_df.iloc[:, 22].astype(str) + " / " + main_df.iloc[:, 23].astype(str),
            "Model Pick": main_df.iloc[:, 25].fillna('') + " " + main_df.iloc[:, 26].fillna('')
        })

        # --- 4. TOP-LEVEL METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        total_games = len(master_table)
        sharp_plays = len(master_table[master_table['Sharp Dog'] != '—'])
        high_ev = len(main_df[(to_n(main_df.iloc[:, 22]) > 10) | (to_n(main_df.iloc[:, 23]) > 10)])

        c1.metric("Total Games", total_games)
        c2.metric("Sharp Targets", sharp_plays)
        c3.metric("High EV Edges", high_ev)
        c4.metric("Market Status", "LIVE", delta="Syncing")

        # --- 5. VISUAL BOARD ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            # Highlight Sharp Target Column
            if row['Sharp Dog'] != '—':
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            # Highlight Model Pick Column
            if row['Model Pick'].strip() != '':
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(
            master_table.style.apply(highlight_logic, axis=1),
            use_container_width=True,
            height=500
        )

        # --- 6. SHARP & EV ANALYSIS PANE ---
        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🎯 Sharp Money Alignment")
            for i, row in master_table.iterrows():
                sharp_dog = row['Sharp Dog']
                pick = row['Model Pick']
                if sharp_dog != '—':
                    if sharp_dog in pick:
                        st.success(f"**CONVICTION**: Sharps & Model both on {sharp_dog}")
                    else:
                        st.warning(f"**CONFLICT**: Sharps on {sharp_dog} | Model on {pick}")

        with col_right:
            st.subheader("📝 Scalping & Entry Notes")
            # Logic for flagging institutional re-entry or high discrepancies
            for i, row in main_df.iterrows():
                away_ev = to_n(row.iloc[22])
                home_ev = to_n(row.iloc[23])
                matchup = f"{row.iloc[0]} @ {row.iloc[1]}"
                
                if away_ev > 20:
                    st.info(f"**Heavy Edge**: {matchup} (Away) shows {away_ev}% EV. Check for Sharp ML confirmation.")
                if home_ev > 20:
                    st.info(f"**Heavy Edge**: {matchup} (Home) shows {home_ev}% EV. Check for Sharp ML confirmation.")

    except Exception as e:
        st.error(f"Tactical Alignment Failure: {e}")
        st.write("Column Index Check: Ensure 'Model' tab matches your standard layout.")
else:
    st.info("🔄 Awaiting Data Sync from 'Model' tab...")
