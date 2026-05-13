import streamlit as st
import pandas as pd

st.set_page_config(page_title="MLB Power Terminal", layout="wide")
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matchups'

st.title("🏹 MLB Institutional Signal Terminal")

try:
    # 1. Load the raw file without skipping anything first
    raw_df = pd.read_csv(url, header=None)
    
    # 2. Find the row index where 'Away Team' actually exists
    # This prevents the 'index out of range' error by locating the data dynamically
    mask = raw_df.apply(lambda x: x.astype(str).str.contains('Away Team', case=False).any(), axis=1)
    if not mask.any():
        st.error("Could not locate 'Away Team' in the Matchups tab. Check sheet headers.")
        st.stop()
    
    target_row = mask.idxmax()
    
    # 3. Rebuild the dataframe from that specific point
    df = raw_df.iloc[target_row:].copy()
    df.columns = df.iloc[0].str.strip() # Clean headers
    df = df.iloc[1:].dropna(subset=[c for c in df.columns if 'Away' in c]).reset_index(drop=True)

    # 4. Identify EV and Sharp columns dynamically
    ev_col = next((c for c in df.columns if 'EV' in str(c).upper()), None)
    sharp_col = next((c for c in df.columns if 'SHARP' in str(c).upper()), None)

    if ev_col and sharp_col:
        df['EV_Num'] = pd.to_numeric(df[ev_col], errors='coerce').fillna(0)
        df['Sharp_Num'] = pd.to_numeric(df[sharp_col], errors='coerce').fillna(0)
        df['Conviction'] = (df['EV_Num'].abs() * 0.7) + (df['Sharp_Num'].abs() * 0.3)

        # Display the Signals
        signals = df[df['Conviction'] > 10].sort_values('Conviction', ascending=False)
        if not signals.empty:
            st.subheader("🔥 High-Intensity Signals")
            st.dataframe(signals.style.background_gradient(cmap='RdYlGn', subset=['Conviction']), use_container_width=True)
        else:
            st.info("No high-conviction alignments found. Scanning...")
            
    else:
        st.warning(f"Found headers but couldn't find 'EV' or 'Sharp'. Columns found: {list(df.columns)}")

except Exception as e:
    st.error(f"Surgical Strike Failed: {e}")
