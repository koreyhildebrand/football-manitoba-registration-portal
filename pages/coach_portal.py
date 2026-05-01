import streamlit as st
import pandas as pd
from utils.helpers import calculate_age_group


def show_coach_portal(players_df: pd.DataFrame, teams_df: pd.DataFrame, name: str, is_admin: bool):
    st.header("🏈 Coach Portal")
    st.subheader(f"Welcome, {name}")

    # ====================== CURRENT YEAR (hard-coded to 2026) ======================
    CURRENT_YEAR = 2026   # ← Change this number if you ever want to update the "current" season

    if st.button("🔄 Refresh My Teams", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    # ====================== FILTER PLAYERS TO CURRENT YEAR ONLY ======================
    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == CURRENT_YEAR]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # ====================== MY TEAMS (only current year) ======================
    if is_admin:
        my_teams = sorted(df["Team Assignment"].dropna().unique().tolist())
    else:
        # Only teams this coach is assigned to in the current year
        coached_teams = teams_df[
            teams_df.get("Coach", "").str.contains(name, case=False, na=False)
        ]["TeamName"].tolist()
        
        my_teams = [team for team in coached_teams if team in df["Team Assignment"].values]

    if not my_teams:
        st.warning(f"You are not currently assigned as coach to any team in the {CURRENT_YEAR} season.")
        return

    selected_team = st.selectbox("Select Team to View", sorted(my_teams), key="coach_team_select")

    # ====================== ROSTER ======================
    coach_roster = df[df.get("Team Assignment", "") == selected_team].copy()

    search = st.text_input("🔍 Search roster", key="coach_search")
    if search:
        coach_roster = coach_roster[coach_roster.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

    display_cols = ["First Name", "Last Name", "AgeGroup", "Contact Phone Number", "Email", "Team Assignment"]
    available_cols = [c for c in display_cols if c in coach_roster.columns]
    st.dataframe(coach_roster[available_cols], width='stretch', hide_index=True)

    # ====================== MEDICAL ALERTS ======================
    st.subheader("⚠️ Medical Alerts")

    details_col = None
    for col in coach_roster.columns:
        if "provide details" in str(col).lower() or "medications, allergies" in str(col).lower():
            details_col = col
            break

    alerts_found = False
    for _, player in coach_roster.iterrows():
        alerts = []
        if player.get("Does your player have a History of Concussions?") == "Yes":
            alerts.append("Concussion History")
        if str(player.get("Does your player have Allergies?", "")).strip() not in ["", "nan", "None", "N/A"]:
            alerts.append("Allergies")
        if player.get("Does your player have Epilepsy?") == "Yes":
            alerts.append("Epilepsy")
        if player.get("Does your player have a Heart Condition?") == "Yes":
            alerts.append("Heart Condition")
        if player.get("Is your player a Diabetic?") == "Yes":
            alerts.append("Diabetic")

        if alerts:
            alerts_found = True
            details = str(player.get(details_col, "")).strip() if details_col else ""
            details_text = f"\n**Details:** {details}" if details and details.lower() not in ["", "nan", "none", "n/a"] else ""

            st.error(
                f"**{player.get('First Name','')} {player.get('Last Name','')}** – "
                f"{' | '.join(alerts)}{details_text}"
            )

    if not alerts_found:
        st.success("No medical alerts for this team.")

    st.caption(f"✅ Coach Portal – {CURRENT_YEAR} Season Only")
