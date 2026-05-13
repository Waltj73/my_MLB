import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 aligns headers with 'Away Team' / 'Home Team' (Row 2 in sheet)
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
        # Standardize empty values to prevent np.False_ errors
        df = df.fillna('')
        
        # Filter for active game rows (Column A length check)
        main_df = df[df.iloc[:, 0].astype(str).str.len() > 2].copy()

        def to_n(v): 
            try: return float(str(v).replace('%','').replace(',','').strip())
            except: return 0.0

        # --- 3. MAPPING (Based on image_1f0f15.png) ---
        # A,B(0,1) | E,F(4,5) | N,O(13,14) | P(15) | S,T(18,19) | W,X(22,23) | Z,AA(25,26) | AB(27 - NEW NOTES)
        master_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "Sharp ML %": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Dog": main_df.iloc[:, 15].astype(str),
            "My Win %": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (A/H)": main_df.iloc[:, 22].astype(str) + " / " + main_df.iloc[:, 23].astype(str),
            "Model Pick": main_df.iloc[:, 25].astype(str) + " " + main_df.iloc[:, 26].astype(str),
            "Tactical Note": main_df.iloc[:, 27].astype(str) if main_df.shape[1] > 27 else ""
        })

        # --- 4. EXECUTIVE METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Games", len(master_table))
        c2.metric("Sharp Targets", len(master_table[master_table['Sharp Dog'].str.len() > 1]))
        
        ev_edges = sum(1 for i, row in main_df.iterrows() if to_n(row.iloc[22]) > 10 or to_n(row.iloc[23]) > 10)
        c3.metric("High EV Edges", ev_edges)
        c4.metric("Market Status", "LIVE")

        # --- 5. VISUAL TACTICAL BOARD ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            # Highlight Sharp Dog column
            if len(str(row['Sharp Dog']).strip()) > 1:
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            # Highlight Model Pick (Green for picks)
            if len(str(row['Model Pick']).strip()) > 1:
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(
            master_table.style.apply(highlight_logic, axis=1),
            use_container_width=True,
            height=450
        )

        # --- 6. SHARP RATIONALE & CONFLICT ANALYSIS ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1:
                    # Detect if sharp dog is actually in the picks
                    if s_dog in pick:
                        st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")
                    else:
                        st.warning(f"**CONFLICT**: Sharps on {s_dog} vs Model Pick: {pick}")

        with col_r:
            st.subheader("📝 Scouting Notes (The 'Why')")
            for _, row in master_table.iterrows():
                note = str(row['Tactical Note']).strip()
                if len(note) > 3:
                    with st.expander(f"Analysis: {row['Matchup']}"):
                        st.write(f"**Field Intelligence**: {note}")
                        # Auto-categorization
                        if any(k in note.lower() for k in ["pitcher", "xera", "fip"]):
                            st.caption("🔍 Case: Pitching Mispricing Identified")
                        elif "wind" in note.lower() or "weather" in note.lower():
                            st.caption("🌬️ Case: Environmental Factor (Total/Side Bias)")
                        elif "lineup" in note.lower() or "scratch" in note.lower():
                            st.caption("📋 Case: Lineup Change / Personnel Shift")

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets 'Model' tab...")
