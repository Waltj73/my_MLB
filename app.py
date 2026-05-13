import streamlit as st
import pandas as pd

# --- 1. THE "STRAT" BRANDING ---
st.set_page_config(page_title="Strat Sniper MLB", layout="wide")
st.markdown("<style>.main { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. DATA CONNECTION ---
# Using your specific Sheet ID and GID for the Model tab
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=30)
def load_strat_data():
    try:
        # Load raw data and skip the first header row to get to the data
        df = pd.read_csv(URL, skiprows=1).fillna('')
        
        # We target the columns exactly as they sit in your sheet:
        # Away(0), Home(1), Sharp%(13), SharpDog(15), EV(23), Pick(25), Notes(27)
        output = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Sharp ML": df.iloc[:, 13].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "EV Edge": df.iloc[:, 23].apply(lambda x: float(str(x).replace('%','')) if x else 0.0),
            "Model Pick": df.iloc[:, 25].astype(str),
            "Tactical Note": df.iloc[:, 27].astype(str)
        })
        return output
    except Exception as e:
        st.error(f"Mapping Error: {e}")
        return pd.DataFrame()

# --- 3. UI & ANALYTICS ---
st.title("🎯 STRAT SNIPER: MLB COMMAND")

df = load_strat_data()

if not df.empty:
    # Sidebar control for EV (The column you clarified as EV, not runs)
    threshold = st.sidebar.slider("Min EV Threshold", 0.0, 15.0, 5.0)
    filtered = df[df['EV Edge'] >= threshold]

    # Main Board
    st.subheader("Tactical Board")
    st.dataframe(filtered.style.background_gradient(cmap='Greens', subset=['EV Edge']), use_container_width=True)

    # Integrated Notes Section
    st.divider()
    st.subheader("📝 Scouting & Market Intelligence")
    
    for _, row in filtered.iterrows():
        # This will show the notes you typed in Column AB
        note = row['Tactical Note'].strip()
        if note:
            with st.expander(f"Analysis: {row['Matchup']}"):
                st.write(f"**Intelligence**: {note}")
                # Logic for the "CONVICTION" flags
                if row['Sharp Dog'] and row['Sharp Dog'] in row['Model Pick']:
                    st.success("🎯 CONVICTION: Sharps & Model Align")
        else:
            # If the note is empty in your sheet, it shows a clean placeholder
            st.caption(f"Waiting for market data on {row['Matchup']}...")

else:
    st.warning("Scanner active: Waiting for Strat setups in current market conditions.")
