import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' # Confirmed "Model" tab from image_1f6ff9.png
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Skip the first merged header row to align with 'Away Team' / 'Home Team' headers
        df = pd.read_csv(URL, skiprows=1)
        # Clean column names for easier manipulation
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
        # Based on image_1f6ff9.png, we map the exact column positions
        # Column A=0, B=1, E=4, F=5, S=18, T=19, W=22, X=23, Z=25, AA=26
        
        # 1. Selection & Cleaning
        # Filter for rows that actually have a team name in Column A
        main_df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0] != '0')].copy()
        
        # 2. Reconstruct the Table for Display
        display_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0] + " @ " + main_df.iloc[:, 1],
            "Vegas Odds (A/H)": main_df.iloc[:, 4].astype(str) + " / " + main_df.iloc[:, 5].astype(str),
            "My Win % (A/H)": main_df.iloc[:, 18].astype(str) + " / " + main_df.iloc[:, 19].astype(str),
            "EV (Away)": main_df.iloc[:, 22],
            "EV (Home)": main_df.iloc[:, 23],
            "Pick": main_df.iloc[:, 25].fillna('') + main_df.iloc[:, 26].fillna('')
        })

        # 3. Apply Highlighting (Green for positive EV)
        def highlight_ev(val):
            try:
                num = float(str(val).replace('%',''))
                color = 'background-color: #c6efce' if num > 0 else ''
                return color
            except:
                return ''

        st.subheader("Today's Projections")
        st.dataframe(
            display_table.style.applymap(highlight_ev, subset=['EV (Away)', 'EV (Home)']),
            use_container_width=True,
            height=600
        )

        # 4. Notes Section
        st.divider()
        st.subheader("📝 Model Notes & Scalping Alerts")
        
        # Automatically pull high EV games into a notes list
        high_ev_games = display_table[
            (pd.to_numeric(display_table['EV (Away)'], errors='coerce') > 10) | 
            (pd.to_numeric(display_table['EV (Home)'], errors='coerce') > 10)
        ]
        
        if not high_ev_games.empty:
            for _, row in high_ev_games.iterrows():
                st.info(f"**High Edge Alert**: {row['Matchup']} shows significant EV. Cross-check Sharp ML before entry.")
        else:
            st.write("No extreme outliers detected in current sync.")

    except Exception as e:
        st.error(f"Table Build Error: {e}")
        st.write("Raw data check:")
        st.dataframe(df.head(5))
else:
    st.info("🔄 Connecting to 'Model' tab... Ensure data is populated in your sheet.")
