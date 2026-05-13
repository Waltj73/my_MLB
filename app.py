import streamlit as st
import pandas as pd

st.set_page_config(page_title="MLB Power Terminal", layout="wide")
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
# Forced CSV export of the Matchups tab
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1263056087'

st.title("🏹 MLB Institutional Signal Terminal")

try:
    # 1. Load the sheet as a raw grid (no headers)
    df = pd.read_csv(url, header=None)
    
    # 2. Identify the data row (we start at index 3 to skip the Model titles)
    # We manually map the columns based on a standard 'Matchups' layout:
    # Col 0: Away | Col 1: Home | Col 6: My Win% | Col 8: EV | Col 9: Sharp
    data = df.iloc[3:].copy()
    
    # 3. Rename columns based on position
    data = data.rename(columns={
        0: "Away Team",
        1: "Home Team",
        8: "EV",
        9: "Sharp"
    })

    # 4. Clean and Convert
    data = data.dropna(subset=["Away Team"]).iloc[:15]
    data['EV_Num'] = pd.to_numeric(data['EV'], errors='coerce').fillna(0)
    data['Sharp_Num'] = pd.to_numeric(data['Sharp'], errors='coerce').fillna(0)
    
    # Calculate the 'Divergence' for your high-conviction trades (like Colorado)
    data['Conviction'] = (data['EV_Num'].abs() * 0.7) + (data['Sharp_Num'].abs() * 0.3)

    # 5. Output the Signal Matrix
    st.subheader("🔥 High-Intensity Signals")
    signals = data[data['Conviction'] > 10].sort_values('Conviction', ascending=False)
    
    if not signals.empty:
        st.dataframe(
            signals[['Away Team', 'Home Team', 'EV', 'Sharp', 'Conviction']]
            .style.background_gradient(cmap='RdYlGn', subset=['Conviction']),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No high-conviction signals found. Is the 'Matchups' tab updated for today?")

except Exception as e:
    st.error(f"Surgical Strike Failed: {e}")
    st.write("Current Sheet Structure (First 5 Rows):")
    st.write(df.head()) # This will show us exactly what Python sees
