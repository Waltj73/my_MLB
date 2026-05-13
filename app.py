import streamlit as st
import pandas as pd
import numpy as np

# --- 1. SYSTEM SETUP ---
st.set_page_config(page_title="MLB Power Terminal", layout="wide")

# This targets your Matchups tab specifically to pull the raw math
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matchups'

# --- 2. THE ENGINE ---
def run_analysis():
    try:
        # Pull the slate and find the 'Away Team' header
        raw_data = pd.read_csv(url)
        header_row = raw_data[raw_data.apply(lambda r: r.astype(str).str.contains('Away Team').any(), axis=1)].index[0]
        
        df = raw_data.iloc[header_row:].copy()
        df.columns = df.iloc[0]
        df = df.iloc[1:].dropna(subset=['Away Team']).reset_index(drop=True)

        # Convert to numeric for our trading logic
        df['EV'] = pd.to_numeric(df['EV'], errors='coerce').fillna(0)
        df['Sharp'] = pd.to_numeric(df['Sharp'], errors='coerce').fillna(0)
        
        # --- LOGIC LAYER: THE "AIR GAP" CALCULATION ---
        # We calculate 'Divergence'—how much the market is moving toward your prediction
        df['Divergence_Score'] = (df['EV'].abs() * 0.6) + (df['Sharp'].abs() * 0.4)
        
        return df
    except Exception as e:
        st.error(f"Engine Startup Failed: {e}")
        return pd.DataFrame()

# --- 3. THE COMMAND CENTER ---
st.title("🏹 MLB Institutional Signal Terminal")
st.markdown("---")

data = run_analysis()

if not data.empty:
    # SECTOR 1: HIGH CONVICTION ALIGNMENTS
    # This captures the +21.08 EV / 16% Sharp move on Colorado
    conviction_threshold = 12
    signals = data[data['Divergence_Score'] >= conviction_threshold].sort_values('Divergence_Score', ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🔥 High-Intensity Signals")
        st.write("Alignment detected between Model EV and Market Flow.")
        
        # We show only the 'Trading' columns
        st.dataframe(
            signals[['Away Team', 'Home Team', 'EV', 'Sharp', 'Divergence_Score']]
            .style.background_gradient(cmap='RdYlGn', subset=['Divergence_Score']),
            use_container_width=True, hide_index=True
        )

    with col2:
        st.subheader("⚠️ Sharp Warnings")
        # Identifies 'Sharp Traps'—where money moves against your EV logic
        traps = data[(data['Sharp'].abs() > 10) & (data['EV'] < 0)]
        for _, row in traps.iterrows():
            st.warning(f"**Trap Alert**: {row['Away Team']} has {row['Sharp']}% Sharp but negative EV.")

    # SECTOR 2: VOLATILITY MATRIX
    st.markdown("---")
    st.subheader("📊 Full Slate Sector Rotation")
    # This helps you see where money is flowing league-wide at a glance
    st.bar_chart(data=data.set_index('Away Team')['Sharp'])

else:
    st.info("Searching for institutional flow signals...")
