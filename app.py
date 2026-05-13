import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # skips Row 1 to hit 'Away Team' / 'Home Team' headers in Row 2
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
        df = df.fillna('')
        main_df = df[df.iloc[:, 0].astype(str).str.len() > 2].copy()

        def to_n(v): 
            try: return float(str(v).replace('%','').replace(',','').strip())
            except: return 0.0

        # --- 3. SAFE MAPPING ---
        def safe_get(idx, name_hint=""):
            if idx < main_df.shape[1]:
                return main_df.iloc[:, idx].astype(str)
            if name_hint in main_df.columns:
                return main_df[name_hint].astype(str)
            return pd.Series([""] * len(main_df))

        master_table = pd.DataFrame({
            "Matchup": safe_get(0) + " @ " + safe_get(1),
            "Vegas Odds": safe_get(4, "Vegas Lines") + " / " + safe_get(5),
            "Sharp ML %": safe_get(13, "Sharp ML %") + " / " + safe_get(14),
            "Sharp Dog": safe_get(15, "Sharp Dog"),
            "My Win %": safe_get(18) + " / " + safe_get(19),
            "EV (A/H)": safe_get(22, "EV") + " / " + safe_get(23),
            "Model Pick": safe_get(25) + " " + safe_get(26),
            "Tactical Note": safe_get(27, "Tactical Note")
        })

        # --- 4. EXECUTIVE METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Games", len(master_table))
        sharp_targets = master_table[master_table['Sharp Dog'].str.len() > 1]
        c2.metric("Sharp Targets", len(sharp_targets))
        
        # Identified via Poisson/wRC+ metrics in your model
        high_ev_list = []
        for i, row in main_df.iterrows():
            if to_n(row.iloc[22]) > 10 or to_n(row.iloc[23]) > 10:
                high_ev_list.append(f"{row.iloc[0]}@{row.iloc[1]}")
        c3.metric("High EV Edges", len(high_ev_list))
        c4.metric("Market Status", "LIVE")

        # --- 5. VISUAL TACTICAL BOARD ---
        st.subheader("Tactical Board")
        
        def highlight_logic(row):
            styles = [''] * len(row)
            if len(str(row['Sharp Dog']).strip()) > 1:
                styles[3] = 'background-color: #d1e7ff; color: #004085; font-weight: bold'
            if len(str(row['Model Pick']).strip()) > 1:
                styles[6] = 'background-color: #c6efce; color: #006100; font-weight: bold'
            return styles

        st.dataframe(
            master_table.style.apply(highlight_logic, axis=1),
            use_container_width=True,
            height=1000, 
            hide_index=True
        )

        # --- 6. INTEGRATED TACTICAL OUTLOOK (NEW SECTION) ---
        st.divider()
        st.subheader("📝 Detailed Tactical Outlook")
        
        out_l, out_r = st.columns(2)
        
        with out_l:
            st.markdown("#### 🔥 Top Sharp Bets & Alignments")
            # Pulling Sharp Dog and Alignment logic directly to the top
            for _, row in master_table.iterrows():
                s_dog = str(row['Sharp Dog']).strip()
                pick = str(row['Model Pick']).strip()
                if len(s_dog) > 1:
                    if s_dog in pick:
                        st.success(f"**ALIGNED**: {row['Matchup']} → Sharps and Model both on **{s_dog}**")
                    else:
                        st.warning(f"**SHARP BIAS**: {row['Matchup']} → Sharps on **{s_dog}** (Model leans {pick})")

        with out_r:
            st.markdown("#### 📈 High EV Model Picks")
            # Logic using your Expected Value (EV) correction
            for i, row in master_table.iterrows():
                ev_str = str(row['EV (A/H)'])
                if any(to_n(x) > 10 for x in ev_str.split('/')):
                    st.info(f"**VALUE EDGE**: {row['Matchup']} → **{row['Model Pick']}** (EV: {ev_str})")

        # --- 7. FIELD NOTES ---
        st.divider()
        st.subheader("🔍 Individual Game Intel")
        for _, row in master_table.iterrows():
            note = str(row['Tactical Note']).strip()
            if len(note) > 3:
                with st.expander(f"Field Note: {row['Matchup']}"):
                    st.write(note)

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("🔄 Syncing with Google Sheets 'Model' tab...")
