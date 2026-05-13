import streamlit as st
import pandas as pd

# --- 1. CONFIG ---
st.set_page_config(page_title="MLB Power Terminal", layout="wide")

SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# Target the 'Matchups' tab
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matchups'

st.title("🏹 MLB Institutional Signal Terminal")
st.markdown("---")

try:
    # 2. THE ENGINE: Load raw and strip all whitespace from headers
    df = pd.read_csv(url, skiprows=2)
    df.columns = df.columns.str.strip() # This kills the hidden spaces causing the error
    
    # Filter for active games
    df = df.dropna(subset=[col for col in df.columns if 'Away Team' in col]).iloc[:15].copy()

    # 3. DYNAMIC COLUMN FINDER
    # We find your columns even if they have weird names like ' EV ' or 'Sharp ML'
    ev_col = [c for c in df.columns if 'EV' in c][0]
    sharp_col = [c for c in df.columns if 'Sharp' in c][0]
    away_col = [c for c in df.columns if 'Away Team' in c][0]
    home_col = [c for c in df.columns if 'Home Team' in c][0]

    # Convert to numeric
    df['EV_Num'] = pd.to_numeric(df[ev_col], errors='coerce').fillna(0)
    df['Sharp_Num'] = pd.to_numeric(df[sharp_col], errors='coerce').fillna(0)
    
    # TRADING LOGIC: Calculate Conviction Score
    df['Conviction'] = (df['EV_Num'].abs() * 0.7) + (df['Sharp_Num'].abs() * 0.3)

    # 4. THE COMMAND CENTER
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔥 High-Intensity Signals")
        # Pulls the Colorado +21.08 EV / 16% Sharp types
        signals = df[df['Conviction'] > 10].sort_values('Conviction', ascending=False)
        
        if not signals.empty:
            st.dataframe(
                signals[[away_col, home_col, ev_col, sharp_col, 'Conviction']]
                .style.background_gradient(cmap='RdYlGn', subset=['Conviction']),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Scanning Matchups... No high-conviction alignments active.")

    with col2:
        st.subheader("⚠️ Institutional Traps")
        # Catching the Pittsburgh/Washington style divergence
        traps = df[(df['Sharp_Num'].abs() > 10) & (df['EV_Num'] < -10)]
        if not traps.empty:
            for _, row in traps.iterrows():
                st.warning(f"**Trap**: {row[away_col]} ({row[sharp_col]} Sharp vs {row[ev_col]} EV)")
        else:
            st.success("No significant Sharp-vs-Model traps detected.")

except Exception as e:
    st.error(f"Syncing... (Technical Log: {e})")
