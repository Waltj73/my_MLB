import streamlit as st
import pandas as pd

# 1. SETUP & BRANDING (Gritty Aesthetic)
st.set_page_config(page_title="Strat Sniper MLB", layout="wide")
st.markdown("<style>.main { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# 2. DATA SOURCE (Targeting your specific Google Sheet)
# Ensure the Sheet is set to "Anyone with the link can view"
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=30)
def load_data():
    try:
        # Pull raw CSV; skipping the first row if it's a sub-header
        df = pd.read_csv(URL, skiprows=1).fillna('')
        return df
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return pd.DataFrame()

# 3. DASHBOARD EXECUTION
st.title("🎯 STRAT SNIPER: MLB COMMAND")

df = load_data()

if not df.empty:
    # Sidebar: EV Threshold (Mapping to Column 23 / X)
    # We use .iloc[:, 23] to ensure we hit the right column regardless of name
    threshold = st.sidebar.slider("Min EV Threshold", 0.0, 15.0, 5.0)
    
    # Process the dataframe for display
    try:
        display_df = pd.DataFrame({
            "Matchup": df.iloc[:, 0] + " @ " + df.iloc[:, 1],
            "Sharp ML%": df.iloc[:, 13],
            "EV Edge": df.iloc[:, 23].apply(lambda x: float(str(x).replace('%','')) if x else 0.0),
            "Model Pick": df.iloc[:, 25],
            "Notes": df.iloc[:, 27]  # Column AB for Intelligence
        })

        # Filter by your EV Threshold
        filtered = display_df[display_df['EV Edge'] >= threshold]

        # Tactical Board
        st.subheader("Tactical Board")
        st.dataframe(filtered.style.background_gradient(cmap='Greens', subset=['EV Edge']), use_container_width=True)

        # 4. THE NOTES INTEGRATION (The "Why")
        st.divider()
        st.subheader("📝 Scouting Notes")
        for _, row in filtered.iterrows():
            if row['Notes']:
                with st.expander(f"Analysis: {row['Matchup']}"):
                    st.write(row['Notes'])
            else:
                st.caption(f"No specific notes for {row['Matchup']}")
                
    except Exception as e:
        st.error("Column Mapping Error. Check if columns were moved in the Sheet.")
        st.write("Current columns detected:", list(df.columns))
else:
    st.warning("Scanner Active: No institutional setups found.")
