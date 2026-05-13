import streamlit as st
import pandas as pd
import numpy as np

# --- 1. TACTICAL CONFIGURATION ---
st.set_page_config(page_title="Strat Sniper | Command", layout="wide")

# Gritty, High-Contrast Theme (E-Squared/Impact Aesthetic)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { border: 1px solid #333; padding: 15px; border-radius: 4px; background-color: #161b22; }
    .stDataFrame { border: 1px solid #333; }
    h1, h2, h3 { color: #e6edf3; font-family: 'Roboto', sans-serif; letter-spacing: -0.5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = '1Jx8nVXHwbqnP7NS-N0MOmsEOWHFDzZjLOFFnOKskMt0'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

@st.cache_data(ttl=15) # Fast 15-second refresh for live scalping
def sync_command_center():
    try:
        # Load raw data and identify specific institutional columns
        df = pd.read_csv(URL, skiprows=1).fillna('')
        
        # Hard-coded indices to ensure data integrity
        # 0:Away, 1:Home, 13:Sharp%, 15:SharpDog, 23:EV, 25:Pick, 27:Notes
        master = pd.DataFrame({
            "Matchup": df.iloc[:, 0].astype(str) + " @ " + df.iloc[:, 1].astype(str),
            "Sharp_Flow": df.iloc[:, 13].astype(str),
            "Sharp_Dog": df.iloc[:, 15].astype(str),
            "EV_Edge": df.iloc[:, 23].apply(lambda x: float(str(x).replace('%','')) if x else 0.0),
            "Strat_Pick": df.iloc[:, 25].astype(str),
            "Tactical_Note": df.iloc[:, 27].astype(str)
        })
        return master
    except Exception as e:
        st.error(f"FATAL SYNC ERROR: {e}")
        return pd.DataFrame()

# --- 3. DASHBOARD INTERFACE ---
def main():
    st.title("🎯 STRAT SNIPER: MLB INSTITUTIONAL SCANNER")
    
    df = sync_command_center()
    
    if not df.empty:
        # Sidebar: The Sniper Filter
        st.sidebar.header("SNIPER SETTINGS")
        ev_min = st.sidebar.slider("Min EV Edge %", 0.0, 15.0, 5.0, help="Filters based on Poisson EV output")
        
        # Filter for the "Alpha" plays
        active_plays = df[df['EV_Edge'] >= ev_min]
        
        # --- TOP LEVEL METRICS ---
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Active Setups", len(active_plays))
        with m2:
            top_ev = active_plays['EV_Edge'].max() if not active_plays.empty else 0
            st.metric("Max EV Edge", f"{top_ev}%")
        with m3:
            st.metric("Market Status", "LIVE" if not df.empty else "CLOSED")

        # --- THE TACTICAL BOARD ---
        st.subheader("Institutional Tactical Board")
        
        # Styled DataFrame for immediate visual recognition
        styled_board = active_plays.style.background_gradient(
            cmap='Greens', subset=['EV_Edge']
        ).format({"EV_Edge": "{:.2f}%"})
        
        st.dataframe(styled_board, use_container_width=True, hide_index=True)

        # --- THE "WHY" (INTEGRATED NOTES & ALIGNMENT) ---
        st.divider()
        st.subheader("📝 Intelligence & Scouting Report")
        
        if not active_plays.empty:
            for _, row in active_plays.iterrows():
                with st.container():
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        # Conviction Logic (Sharps + Model Alignment)
                        s_dog = str(row['Sharp_Dog']).strip()
                        pick = str(row['Strat_Pick']).strip()
                        
                        if s_dog and s_dog in pick:
                            st.success(f"**CONVICTION**: {row['Matchup']}")
                            st.caption(f"Sharps & Model align on {s_dog}")
                        elif s_dog:
                            st.warning(f"**CONFLICT**: {row['Matchup']}")
                            st.caption(f"Sharps: {s_dog} | Model: {pick}")
                        else:
                            st.info(f"**MODEL ONLY**: {row['Matchup']}")

                    with c2:
                        # The Tactical Note (Column AB / 27)
                        note = row['Tactical_Note']
                        if note and len(note) > 3:
                            st.info(f"**ANALYSIS**: {note}")
                        else:
                            st.caption("Awaiting field data for this matchup...")
                    st.write("---")
        else:
            st.warning("No plays currently meet the Sniper EV Threshold.")

    else:
        st.error("Connection Lost: No data found in the designated command sheet.")

if __name__ == "__main__":
    main()
