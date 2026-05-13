import streamlit as st
import pandas as pd

# --- 1. CONFIG ---
st.set_page_config(page_title="MLB Power Terminal", layout="wide")

# This ID points to your '2026 MLB Model'
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# Target the 'Matchups' tab directly
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matchups'

st.title("🏹 MLB Institutional Signal Terminal")
st.markdown("---")

try:
    # 2. THE ENGINE: We skip exactly 2 rows to land on 'Away Team'
    df = pd.read_csv(url, skiprows=2)
    
    # Clean up any 'ghost' rows from the Google Sheet export
    df = df.dropna(subset=['Away Team']).iloc[:15].copy()

    # Convert the core math to numbers
    df['EV'] = pd.to_numeric(df['EV'], errors='coerce').fillna(0)
    df['Sharp'] = pd.to_numeric(df['Sharp'], errors='coerce').fillna(0)
    
    # 3. TRADING LOGIC: Calculate Conviction
    # We weight EV heavily but require Sharp confirmation
    df['Conviction'] = (df['EV'].abs() * 0.7) + (df['Sharp'].abs() * 0.3)

    # 4. THE COMMAND CENTER
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔥 High-Intensity Signals")
        # Filters for the Colorado-style edges (+21.08 EV / 16.0% Sharp)
        signals = df[df['Conviction'] > 10].sort_values('Conviction', ascending=False)
        
        if not signals.empty:
            st.dataframe(
                signals[['Away Team', 'Home Team', 'EV', 'Sharp', 'Conviction']]
                .style.background_gradient(cmap='RdYlGn', subset=['Conviction']),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Scanning Matchups... No high-conviction alignments currently active.")

    with col2:
        st.subheader("⚠️ Institutional Traps")
        # Flags where money moves against your math (e.g. Pittsburgh -68.69 EV)
        traps = df[(df['Sharp'].abs() > 10) & (df['EV'] < -10)]
        if not traps.empty:
            for _, row in traps.iterrows():
                st.warning(f"**Trap**: {row['Away Team']} ({row['Sharp']}% Sharp vs {row['EV']} EV)")
        else:
            st.success("No significant Sharp-vs-Model traps detected.")

except Exception as e:
    st.error(f"Syncing... (Technical Log: {e})")
