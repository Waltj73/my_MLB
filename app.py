import streamlit as st
import pandas as pd

st.set_page_config(page_title="MLB Power Terminal", layout="wide")

# This is the GID for your 'Matchups' tab
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '1263056087' 
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

st.title("🏹 MLB Institutional Signal Terminal")

# Initialize df so the error you saw doesn't happen again
df = pd.DataFrame()

try:
    # 1. Pull the data
    df = pd.read_csv(url, header=None)
    
    if not df.empty:
        st.success("Connection Successful. Analyzing Grid...")
        
        # 2. Display the raw grid so you can tell me which columns are which
        st.subheader("🔍 Raw Data Preview (First 10 Rows)")
        st.write("Check this table to see which columns contain 'Away Team', 'EV', and 'Sharp'.")
        st.dataframe(df.head(10))
        
        # 3. Basic Mapping (Adjust these numbers based on what you see in the preview)
        # Based on your previous model structure:
        # Col 0 = Away, Col 1 = Home, Col 8 = EV, Col 9 = Sharp
        data = df.iloc[3:].copy() 
        data.columns = [f"Col_{i}" for i in range(len(data.columns))]
        
        # 4. Display a simple "Quick Look" at the trade edges
        if "Col_0" in data.columns and "Col_8" in data.columns:
            st.subheader("⚡ Quick Edge Scan")
            data['EV_Num'] = pd.to_numeric(data['Col_8'], errors='coerce').fillna(0)
            data['Sharp_Num'] = pd.to_numeric(data['Col_9'], errors='coerce').fillna(0)
            
            # Show only games with your +12 EV / +10% Sharp criteria
            signals = data[(data['EV_Num'].abs() > 12) | (data['Sharp_Num'].abs() > 10)]
            st.table(signals[['Col_0', 'Col_1', 'Col_8', 'Col_9']])
            
    else:
        st.error("The sheet returned no data. Check if the GID is correct.")

except Exception as e:
    st.error(f"Engine Failure: {e}")
