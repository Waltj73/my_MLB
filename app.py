import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' # Confirmed "Model" tab from image_1f6ff9.png
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Skip the first merged header row
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI & TABLE GENERATION ---
st.set_page_config(page_title="MLB Model Dashboard", layout="wide")
st.title("⚾ 2026 MLB Tactical Board")

df = load_data()

if not df.empty:
    try:
        # Filter for rows with actual data in Column A (Away Team)
        main_df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0] != '0')].copy()
        
        # 2. Map Columns based on image_1f6ff9.png
        # A=0, B=1, E=4, F=5, S=18, T=19, W=22, X=23, Z=25, AA=26
        display_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Vegas Odds (A/H)": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "My Win % (A/H)": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (Away)": main_df.iloc[:, 22],
            "EV (Home)": main_df.iloc[:, 23],
            "Picks": main_df.iloc[:, 25].fillna('') + " " + main_df.iloc[:, 26].fillna('')
        })

        # 3. Apply Highlighting (Fixed Styler Method)
        def highlight_ev(val):
            try:
                num = float(str(val).replace('%',''))
                return 'background-color: #c6efce; color: #006100' if num > 0 else ''
            except:
                return ''

        st.subheader("Today's Projections")
        # Use .map() instead of .applymap() for current Pandas versions
        st.dataframe(
            display_table.style.map(highlight_ev, subset=['EV (Away)', 'EV (Home)']),
            use_container_width=True,
            height=600
        )

        # 4. Notes & Tactical Alerts
        st.divider()
        st.subheader("📝 Tactical Notes")
        
        # Pull high EV matchups for quick review
        high_edge = display_table[
            (pd.to_numeric(display_table['EV (Away)'], errors='coerce') > 15) | 
            (pd.to_numeric(display_table['EV (Home)'], errors='coerce') > 15)
        ]
        
        if not high_edge.empty:
            for _, row in high_edge.iterrows():
                st.success(f"**Action Required**: {row['Matchup']} showing 15%+ EV. Verify starting lineups.")
        else:
            st.info("No extreme EV outliers detected. Proceed with standard model picks.")

    except Exception as e:
        st.error(f"Table Alignment Error: {e}")
        st.write("Headers found in sheet:", list(df.columns))
else:
    st.info("🔄 Connecting to Model... Ensure the Google Sheet is shared.")
