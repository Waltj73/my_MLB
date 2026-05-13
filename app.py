with sharp_tab:

    st.subheader("🔥 Sharp Money Targets")

    for _, row in master_table.iterrows():

        sharp_team = normalize_team(
            row["Sharp Dog"]
        )

        if not sharp_team:
            continue

        model_team = normalize_team(
            first_word(
                row["Model Pick"]
            )
        )

        aligned = (
            sharp_team
            and
            sharp_team == model_team
        )

        if aligned:

            st.success(
                f"{row['Matchup']} → {sharp_team} "
                f"(Sharps + Model)"
            )

        else:

            st.warning(
                f"{row['Matchup']} → {sharp_team} "
                f"(Sharp Only)"
            )
