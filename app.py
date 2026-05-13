import streamlit as st
import pandas as pd
import cloudscraper
import io

# --- TACTICAL ANALYSIS ENGINE ---
def get_pick_details(row):
    """Generates detailed scouting notes for the tactical dashboard."""
    notes = []
    if row['EV'] > 5:
        notes.append(f"🎯 **High Value**: Your model shows a {row['Edge']:.1f}% edge over market implied odds.")
    if row['Sharp_Diff'] > 15:
        notes.append(f"🐳 **Sharp Action**: Professionals are heavy on this side ({row['Sharp_Diff']:.1f}% divergence).")
    if row['EV'] < 0 and row['Sharp_Diff'] > 20:
        notes.append("⚠️ **Trap Game**: Heavy sharp interest despite low model EV. Market may know something.")
    
    return " | ".join(notes) if notes else "No significant tactical deviation."

# --- MAIN DASHBOARD ---
st.title("⚾ MLB Full Slate Tactical Dashboard")

df = fetch_vsin_splits() # Using your existing fetch function

if not df.empty:
    # 1. DATA ALIGNMENT (from your May 13th screenshot)
    team_col = 'MLB - Wednesday, May 13May 13.1'
    handle_col = 'HandleHND.2'
    bets_col = 'BetsBET.2'
    
    # 2. ENSURE NUMERIC TYPES (Prevents Styler errors)
    df['Odds'] = pd.to_numeric(df['MoneyML'], errors='coerce')
    df['Handle_Val'] = df[handle_col].astype(str).str.extract('(\d+)').astype(float)
    df['Bets_Val'] = df[bets_col].astype(str).str.extract('(\d+)').astype(float)
    
    # 3. CALCULATIONS
    df['Sharp_Diff'] = df['Handle_Val'] - df['Bets_Val']
    df['My_Win_Prob'] = 0.55  # Placeholder: Replace with your model's actual Win %
    
    # Calculate EV and Market Edge
    df['Implied_Prob'] = df['Odds'].apply(lambda x: 100/(x+100) if x > 0 else abs(x)/(abs(x)+100))
    df['EV'] = df.apply(lambda x: calculate_ev(x['My_Win_Prob'], x['Odds']), axis=1) # Using your EV function
    df['Edge'] = (df['My_Win_Prob'] * 100) - (df['Implied_Prob'] * 100)

    # 4. MASTER TABLE WITH GRADIENTS
    st.subheader("📊 Full Slate Analysis")
    display_cols = [team_col, 'Odds', 'My_Win_Prob', 'EV', 'Edge', 'Sharp_Diff']
    
    # Apply coloring (Requires matplotlib in requirements.txt)
    styled_df = df[display_cols].style.background_gradient(
        subset=['EV', 'Sharp_Diff', 'Edge'], 
        cmap='RdYlGn'
    ).format({
        'My_Win_Prob': '{:.1%}',
        'EV': '{:.2f}%',
        'Edge': '{:+.1f}%',
        'Sharp_Diff': '{:+.1f}%'
    })
    
    st.dataframe(styled_df, hide_index=True, use_container_width=True)

    # 5. DETAILED SCOUTING NOTES
    st.divider()
    st.subheader("🧠 Tactical Pick Notes")
    
    # Only show notes for games with significant interest
    significant_games = df[(abs(df['EV']) > 2) | (abs(df['Sharp_Diff']) > 10)]
    
    for _, row in significant_games.iterrows():
        with st.expander(f"Scouting Report: {row[team_col]}"):
            st.write(get_pick_details(row))
            st.metric("Model Edge", f"{row['Edge']:.1f}%", delta=f"{row['EV']:.2f} EV")
