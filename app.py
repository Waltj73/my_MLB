import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- 1. CONFIG & BRANDING ---
# Using the high-contrast, moody aesthetic requested for the brand
st.set_page_config(page_title="Strat Sniper MLB", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { border: 1px solid #333; padding: 10px; border-radius: 5px; }
    div[data-testid="stExpander"] { background-color: #1a1c23; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA SOURCE & MAPPING ---
# GID 0 targets the primary model tab in your Google Sheet
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
GID = '0' 
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'

@st.cache_data(ttl=30)
def load_and_sync_data():
    try:
        # Skip top row to hit headers, then map specific columns
        df = pd.read_csv(URL, skiprows=1).fillna('')
        
        # Mapping based on your specific spreadsheet structure
        # Columns: Away(0), Home(1), Sharp%(13,14), SharpDog(15), EV(23), ModelPick(25), Note(27)
        master = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Sharp ML %": df.iloc[:, 13].astype(str) + " / " + df.iloc[:, 14].astype(str),
            "Sharp Dog": df.iloc[:, 15].astype(str),
            "EV Edge": df.iloc[:, 23].apply(lambda x: float(str(x).replace('%','')) if x else 0.0),
            "Model Pick": df.iloc[:, 25].astype(str),
            "Tactical Note": df.iloc[:, 27].astype(str)
        })
        return master
    except Exception as e:
        st.error(f"Sync Error: {e}. Check if Sheet is set to 'Anyone with link can view'.")
        return pd.DataFrame()

# --- 3. AUTOMATED INTELLIGENCE ---
@st.cache_data(ttl=3600)
def fetch_market_intel():
    """Placeholder for the scraping logic to avoid manual 'Intelligence' entry."""
    # This maps to the Scouting Notes if your Column AB is empty
    return {
        "Washington @ Cincinnati": "Wind 16mph out to CF. Lodolo early-season rust vs Abrams' 27% barrel rate.",
        "Mariners @ Astros": "McCullers Jr. struggling (9.39 ERA). Sharp pressure on SEA moneyline.",
        "Rockies @ Pirates": "Reverse Line Movement detected. 10% Money/Ticket gap on Colorado."
    }

# --- 4. DASHBOARD EXECUTION ---
def main():
    st.title("🎯 STRAT SNIPER: MLB TACTICAL COMMAND")
    
    df = load_and_sync_data()
    intel_db = fetch_market_intel()
    
    if not df.empty:
        # Sidebar: The EV Threshold (based on your clarified EV column)
        threshold = st.sidebar.slider("Minimum EV Edge (%)", 0.0, 15.0, 5.0)
        filtered_df = df[df['EV Edge'] >= threshold]

        # Display the Board
        st.subheader("Tactical Board")
        
        def highlight_picks(row):
            styles = [''] * len(row)
            # Highlight high-conviction Sharp Dogs
            if len(row['Sharp Dog']) > 2:
                styles[2] = 'background-color: #1e293b; color: #38bdf8; font-weight: bold'
            # Highlight the EV Edge
            styles[3] = 'background-color: #064e3b; color: #4ade80;'
            return styles

        st.dataframe(
            filtered_df.style.apply(highlight_picks, axis=1), 
            use_container_width=True,
            hide_index=True
        )

        # Analysis Pane
        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("⚖️ Sharp vs. Model Alignment")
            for _, row in filtered_df.iterrows():
                s_dog = row['Sharp Dog'].strip()
                pick = row['Model Pick'].strip()
                
                if s_dog and s_dog in pick:
                    st.success(f"**CONVICTION**: Sharps & Model both on {s_dog}")
                elif s_dog:
                    st.warning(f"**CONFLICT**: Sharps on {s_dog} | Model on {pick}")

        with col_r:
            st.subheader("📝 Scouting Notes (The 'Why')")
            for _, row in filtered_df.iterrows():
                # Use Sheet Note if exists, otherwise fallback to Auto-Intel
                note = row['Tactical Note'] if len(row['Tactical Note']) > 3 else intel_db.get(row['Matchup'], "No significant market alerts.")
                
                with st.expander(f"Analysis: {row['Matchup']}"):
                    st.write(note)
                    if "wind" in note.lower(): st.caption("🌬️ Weather Factor")
                    if "era" in note.lower() or "pitcher" in note.lower(): st.caption("🔍 Pitching Edge")

    else:
        st.warning("Scanner Active: No institutional setups found for current market conditions.")

if __name__ == "__main__":
    main()
