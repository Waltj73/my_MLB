import streamlit as st
---

### 📊 Model Edge

- Vegas Win %: **{vegas_pct:.2f}%**
- Model Win %: **{win_pct:.2f}%**
- Difference: **{edge:.2f}%**
- Expected Value: **{ev:.2f}**

---

### 🧠 Analysis

Your model projects {team} as undervalued by the market.

The current betting line implies a lower probability than your projections suggest, creating a positive EV opportunity.

Against {opponent}, the statistical edge is large enough to justify consideration as a moneyline play.

---

### 💰 Sharp Money

{sharp_text}

---

### ⚠️ Risk Notes

- MLB variance is high
- Bullpen volatility matters
- Do not over-size positions based on one edge alone
"""


# =====================================================
# BUILD PICKS COLUMN
# =====================================================

picks = []

for _, row in results_df.iterrows():
    pick, side = moneyline_label(row)
    picks.append(pick)

results_df["Pick"] = picks


# =====================================================
# MAIN DASHBOARD
# =====================================================

st.title("⚾ MLB Betting Dashboard")

st.subheader("📋 Model Table")
st.dataframe(results_df, use_container_width=True)


# =====================================================
# TOP PLAYS
# =====================================================

st.subheader("🔥 Top Plays")

play_df = results_df[
    (
        (results_df["Away EV"] > 10)
        |
        (results_df["Home EV"] > 10)
    )
]

st.dataframe(play_df, use_container_width=True)


# =====================================================
# AUTO WRITE-UPS
# =====================================================

st.subheader("📝 Auto Game Write-Ups")

for _, row in results_df.iterrows():
    st.markdown(generate_game_writeup(row))
    st.divider()
