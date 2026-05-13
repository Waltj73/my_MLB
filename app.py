import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="MLB Power Terminal", layout="wide")

# --- 1. HARD-CODED IDENTIFIERS ---
# Double-check these from your browser URL:
# Spreadsheet ID: 1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0
# Matchups GID: 1263056087
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1263056087'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

st.title("🏹 MLB Institutional Signal Terminal")

try:
    # 2. REQUEST DATA WITH BROWSER HEADERS (Fixes 400/403 Errors)
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Load the raw CSV from the response content
        raw_df = pd.read_csv(io.StringIO(response.text), header=None)
        
        st.success("Live Feed Connected.")
        
        # 3. DIAGNOSTIC GRID
        # This shows you EXACTLY what is on your sheet right now
        st.subheader("🔍 Raw Matchups Preview")
        st.dataframe(raw_df.head(10))
        
        # 4. SIGNAL LOGIC (Mapping to your specific columns)
        # Based on your 'Matchups' tab:
        # Col 0 = Away Team | Col 1 = Home Team | Col 8 = EV | Col 9 = Sharp
        data = raw_df.iloc[3:].copy()
        data.columns = [f"Col_{i}" for i in range(len(data.columns))]
        
        # Convert the math
        data['EV_Num'] = pd.to_numeric(data['Col_8'], errors='coerce').fillna(0)
        data['Sharp_Num'] = pd.to_numeric(data['Col_9'], errors='coerce').fillna(0)
        
        # 5. HIGH-INTENSITY SIGNAL DISPLAY
        # Target the "Colorado-style" +21.08 EV and +16% Sharp signals
        signals = data[(data['EV_Num'].abs() >= 12) & (data['Sharp_Num'].abs() >= 10)]
        
        if not signals.empty:
            st.subheader("🔥 Institutional Buy Signals")
            st.table(signals[['Col_0', 'Col_1', 'Col_8', 'Col_9']])
        else:
            st.info("Scanning... No high-conviction alignments on the current slate.")
            
    else:
        st.error(f"Data Feed Rejected: HTTP {response.status_code}")
        st.info("Check: Is the sheet set to 'Anyone with the link can view'?")

except Exception as e:
    st.error(f"Terminal Crash: {e}")
