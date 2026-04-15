import streamlit as st
import pandas as pd
from utils.helpers import calculate_age_group


def show_coach_portal(players_df: pd.DataFrame, teams_df: pd.DataFrame, name: str, is_admin: bool):
    st.header("🏈 Coach Portal")
    st.subheader(f"Welcome, {name}")

    if st.button("🔄 Refresh My Teams", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    if is_admin:
        my_teams = teams_df["TeamName"].dropna().unique().tolist()
    else:
        my_teams = teams_df[teams_df.get("Coach", "").str.contains(name, case=False, na=False)]["TeamName"].tolist()

    if not my_teams:
        st.warning("You are not currently assigned as coach to any team.")
        return

    selected_team = st.selectbox("Select Team to View", my_teams, key="coach_team_select")
    coach_roster = players_df[players_df.get("Team Assignment", "") == selected_team].copy()

    search = st.text_input("🔍 Search roster", key="coach_search")
    if search:
        coach_roster = coach_roster[coach_roster.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

    display_cols = ["First Name", "Last Name", "AgeGroup", "Contact Phone Number", "Email", "Team Assignment"]
    available_cols = [c for c in display_cols if c in coach_roster.columns]
    st.dataframe(coach_roster[available_cols], width='stretch', hide_index=True)

    st.subheader("⚠️ Medical Alerts")
    alerts_found = False
    for _, player in coach_roster.iterrows():
        alerts = []
        if player.get("Does your player have a History of Concussions?") == "Yes": alerts.append("Concussion History")
        if str(player.get("Does your player have Allergies?", "")).strip() not in ["", "nan", "None", "N/A"]: alerts.append("Allergies")
        if player.get("Does your player have Epilepsy?") == "Yes": alerts.append("Epilepsy")
        if player.get("Does your player have a Heart Condition?") == "Yes": alerts.append("Heart Condition")
        if player.get("Is your player a Diabetic?") == "Yes": alerts.append("Diabetic")
        if alerts:
            alerts_found = True
            st.error(f"**{player.get('First Name','')} {player.get('Last Name','')}** – {' | '.join(alerts)}")
    if not alerts_found:
        st.success("No medical alerts for this team.")
