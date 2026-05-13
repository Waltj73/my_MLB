import streamlit as st
import pandas as pd
import numpy as np

# --- 1. DATA SYNC (Model Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skiprows=1 aligns headers with 'Away Team' / 'Home Team'
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
        # Standardize empty values to prevent the np.False_ error during filtering
        df = df.fillna('')
        
        # Filter for active games (Rows where Column A has a team name)
        main_df = df[df.iloc[:, 0].astype(str).str.len() > 2].copy()

        def to_n(v): 
            try:
                return float(str(v).replace('%','').replace(',','').strip())
            except:
                return 0.0

        # --- 3. THE MASTER DATA TABLE (image_1f6ff9.png Mapping) ---
        # A,B(0,1) | E,F(4,5) | N,O(13,14) | P(15) | S,T(18,19) | W,X(22,23) | Z,AA(25,26)
        master_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "Sharp ML %": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Dog": main_df.iloc[:, 15].astype(str),
            "My Win %": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (A/H)": main_df.iloc[:, 22].astype(str) + " / " + main_df.iloc[:, 23].astype(str),
            "Model Pick": main_df.iloc[:, 25].astype(str) + " " + main_df.iloc[:, 26].astype(str)
        })

        # --- 4. TOP-LEVEL METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Games", len(master_table))
        # Counts non-empty "Sharp Dog" entries
        c2.metric("Sharp Targets", len(master_table[master_table['Sharp Dog'].str.len() > 1]))
        
        # High EV calculation for scalping alerts
        ev_count = 0
        for i, row in main_df.iterrows():
            if to_n(row.iloc[22]) > 10 or to_n(row.iloc[23]) > 10:
                ev_count += 1
        c3.metric("High EV Edges", ev_count)
        c4.metric("Market Status", "LIVE")

        # --- 5. VISUAL BOARD ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            # Highlight Sharp Target (Col 3)
            if len(str(row['Sharp Dog']).strip()) > 1:
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            # Highlight Model Pick (Col 6)
            if len(str(row['Model Pick']).strip()) > 1:
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(
            master_table.style.apply(highlight_logic, axis=1),
            use_container_width=True,
            height=450
        )

        # --- 6. SHARP & EV ANALYSIS PANE ---
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("🎯 Sharp Money Alignment")
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1:
                    if s_dog in pick:
                        st.success(f"**CONVICTION**: Sharps & Model on {s_dog}")
                    else:
                        st.warning(f"**CONFLICT**: Sharps on {s_dog} vs Model on {pick}")

        with col_r:
            st.subheader("📝 Entry Notes")
            for _, row in main_df.iterrows():
                a_ev, h_ev = to_n(row.iloc[22]), to_n(row.iloc[23])
                if a_ev > 20 or h_ev > 20:
                    team = row.iloc[0] if a_ev > 20 else row.iloc[1]
                    val = a_ev if a_ev > 20 else h_ev
                    st.info(f"**Heavy Edge**: {team} shows {val:.1f}% EV. Cross-verify Sharp ML.")

    except Exception as e:
        st.error(f"Logic Error: {e}")
        st.write("Headers seen by app:", list(df.columns))
else:
    st.info("🔄 Connecting to 'Model' tab...")
