import streamlit as st
import pandas as pd

# --- 1. DATA SYNC (Targeting "Model" Tab) ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=15)
def load_data():
    try:
        # Skip the first merged header row to align with 'Away Team' / 'Home Team'
        df = pd.read_csv(URL, skiprows=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# --- 2. UI & TABLE GENERATION ---
st.set_page_config(page_title="MLB Sharp Analysis", layout="wide")
st.title("⚾ MLB Sharp Analysis & Tactical Board")

df = load_data()

if not df.empty:
    try:
        # Filter for rows with actual team data
        main_df = df[df.iloc[:, 0].notna() & (df.iloc[:, 0] != '0')].copy()
        
        # COLUMN MAPPING (Based on image_1f6ff9.png)
        # N=13, O=14 (Sharps ML), P=15 (Sharp Dogs), W=22, X=23 (EV)
        display_table = pd.DataFrame({
            "Matchup": main_df.iloc[:, 0].astype(str) + " @ " + main_df.iloc[:, 1].astype(str),
            "Sharp ML (A/H)": main_df.iloc[:, 13].astype(str) + " / " + main_df.iloc[:, 14].astype(str),
            "Sharp Target": main_df.iloc[:, 15].fillna('—'),
            "EV (Away)": main_df.iloc[:, 22],
            "EV (Home)": main_df.iloc[:, 23],
            "Picks": main_df.iloc[:, 25].fillna('') + " " + main_df.iloc[:, 26].fillna('')
        })

        # --- SHARP FILTERING LOGIC ---
        # Identify "Sharp Alignment" (When Sharp Target matches your Model Pick or high EV)
        def to_n(v): return pd.to_numeric(str(v).replace('%','').strip(), errors='coerce')

        st.subheader("🎯 Sharp Money Movement")
        
        # Create columns for the summary cards
        c1, c2, c3 = st.columns(3)
        
        # Logic for Sharp Alerts
        sharp_alerts = []
        for i, row in display_table.iterrows():
            away_sharp = to_n(main_df.iloc[i, 13])
            home_sharp = to_n(main_df.iloc[i, 14])
            
            # Identify games where sharps have > 5% movement or a specific dog is flagged
            if abs(away_sharp) > 5 or abs(home_sharp) > 5 or row['Sharp Target'] != '—':
                sharp_alerts.append(row)

        c1.metric("Sharp Targets Identified", len([x for x in display_table['Sharp Target'] if x != '—']))
        
        # --- MAIN BOARD ---
        st.divider()
        def highlight_sharp(val):
            return 'background-color: #d1e7ff; color: #004085; font-weight: bold' if val != '—' else ''

        st.dataframe(
            display_table.style.map(highlight_sharp, subset=['Sharp Target']),
            use_container_width=True,
            height=500
        )

        # --- 3. TACTICAL BREAKDOWN ---
        st.subheader("📝 Sharp vs. Model Alignment")
        
        if sharp_alerts:
            for alert in sharp_alerts:
                # Check if sharp target matches your pick column
                is_aligned = alert['Sharp Target'] in alert['Picks'] if alert['Sharp Target'] != '—' else False
                
                with st.expander(f"Analysis: {alert['Matchup']}"):
                    st.write(f"**Sharp Action**: {alert['Sharp ML (A/H)']}")
                    st.write(f"**Flagged Dog**: {alert['Sharp Target']}")
                    if is_aligned:
                        st.success("✅ **Alignment**: Professional money is following the model's pick.")
                    elif alert['Sharp Target'] != '—':
                        st.warning("⚠️ **Conflict**: Sharps are on the opposite side of the model's projection.")
        else:
            st.write("No significant sharp discrepancies detected in the current feed.")

    except Exception as e:
        st.error(f"Alignment Error: {e}")
else:
    st.info("🔄 Connecting to Model...")
