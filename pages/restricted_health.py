import streamlit as st
import pandas as pd


def show_restricted_health(players_df: pd.DataFrame, teams_df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list):
    st.header("🔒 Restricted Health Data")

    # Team selector
    if can_see_all_teams:
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    else:
        team_options = sorted([t for t in teams_df["TeamName"].dropna().unique().tolist() if t in allowed_teams])

    selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

    if selected_team == "All Teams":
        roster = players_df.copy()
    else:
        roster = players_df[players_df.get("Team Assignment", "") == selected_team].copy()

    if roster.empty:
        st.info("No players found for the selected team.")
        return

    st.subheader(f"Roster for {selected_team}")

    # Robust lookup for the medical details column
    details_col = None
    for col in roster.columns:
        col_str = str(col).lower()
        if "provide details" in col_str or "medications, allergies" in col_str:
            details_col = col
            break

    for _, player in roster.iterrows():
        alerts = []
        if player.get("Does your player have a History of Concussions?") == "Yes":
            alerts.append("Concussion")
        if str(player.get("Does your player have Allergies?", "")).strip() not in ["", "nan", "None", "N/A"]:
            alerts.append("Allergies")
        if player.get("Does your player have Epilepsy?") == "Yes":
            alerts.append("Epilepsy")
        if player.get("Does your player have a Heart Condition?") == "Yes":
            alerts.append("Heart Condition")
        if player.get("Is your player a Diabetic?") == "Yes":
            alerts.append("Diabetic")

        alert_text = " | ".join(alerts) if alerts else ""

        # Build the top bar (expander title) with medical details included
        details = ""
        if details_col and details_col in player:
            details = str(player[details_col]).strip()
            if details and details.lower() not in ["", "nan", "none", "n/a"]:
                details = f" | Details: {details}"

        title = f"{player.get('First Name','')} {player.get('Last Name','')}"
        if alert_text:
            title += f" ⚠️ {alert_text}{details}"
        else:
            title += details

        with st.expander(title):
            # Inside the expander we still show the full details for clarity
            if alert_text:
                st.error(f"**MEDICAL ALERT:** {alert_text}")

            st.write(f"**Birthdate:** {player.get('Birthdate', 'N/A')}")
            st.write(f"**MB Health Number:** {player.get('MB Health Number:', 'N/A')}")
            st.write(f"**History of Concussions:** {player.get('Does your player have a History of Concussions?', 'No')}")
            st.write(f"**Allergies:** {player.get('Does your player have Allergies?', 'None')}")
            st.write(f"**Epilepsy:** {player.get('Does your player have Epilepsy?', 'No')}")
            st.write(f"**Heart Condition:** {player.get('Does your player have a Heart Condition?', 'No')}")
            st.write(f"**Diabetic:** {player.get('Is your player a Diabetic?', 'No')}")
            st.write(f"**Asthma:** {player.get('Does your player have Asthma?', 'No')}")
            st.write(f"**Medication:** {player.get('Does your player take any Medications?', 'None')}")

            if details_col and details_col in player:
                details_text = str(player[details_col]).strip()
                if details_text and details_text.lower() not in ["", "nan", "none", "n/a"]:
                    st.write(f"**Medical Details / Medications / Allergies:** {details_text}")

    st.caption("✅ Restricted Health Data")
