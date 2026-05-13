# --- 1. UPDATED DATA SYNC ---
# Assuming Column AB is Index 27
col_note = 27 

# --- 2. UPDATED TACTICAL BOARD ---
master_table["Context"] = main_df.iloc[:, col_note].astype(str)

st.subheader("Tactical Board")
st.dataframe(
    master_table.style.apply(highlight_logic, axis=1),
    column_config={
        "Context": st.column_config.TextColumn(
            "Tactical Note 📝",
            help="Sharp rationale: Pitcher metrics, weather, or lineup shifts.", # Tooltip header
            width="large"
        )
    },
    use_container_width=True
)

# --- 3. THE "WHY" PANEL ---
st.divider()
st.subheader("🕵️ Sharp Rationale Breakdown")

for i, row in master_table.iterrows():
    note = row['Context'].strip()
    if len(note) > 5: # Only show if there is an actual note
        with st.expander(f"The Case for {row['Matchup']}"):
            st.write(f"**Field Intelligence**: {note}")
            # Logic to identify 'why' based on keywords in your note
            if "pitcher" in note.lower():
                st.caption("🎯 Analysis: This is a pitching-driven edge (xERA/FIP correction).")
            elif "wind" in note.lower() or "weather" in note.lower():
                st.caption("🌬️ Analysis: Environmental factors are suppressing/boosting runs.")
