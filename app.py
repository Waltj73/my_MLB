import streamlit as st
import pandas as pd
import requests
import io

# 1. LIVE ID CHECK
# Ensure these match your browser URL exactly:
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1263056087' 
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

st.title("🏹 MLB Institutional Signal Terminal")

try:
    # 2. THE BROWSING HANDSHAKE
    # We mimic a real user to get past Google's basic bot filters
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        # 3. DATA RECOVERY
        # We read the raw text and force the header to start at your data row
        df = pd.read_csv(io.StringIO(response.text), skiprows=2)
        df.columns = df.columns.str.strip() # Kill invisible spaces

        st.success("Feed Online.")
        st.subheader("🔥 High-Conviction Matchups")
        
        # Display the core 'Trading' columns you rely on
        st.dataframe(df.head(15), use_container_width=True)
        
    else:
        st.error(f"Feed Error {response.status_code}: Google rejected the request.")

except Exception as e:
    st.error(f"Connection Failed: {e}")
