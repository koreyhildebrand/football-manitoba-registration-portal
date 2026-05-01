import streamlit as st
import pandas as pd
import datetime


def show_restricted_health(players_df: pd.DataFrame, teams_df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list):
    st.header("🔒 Restricted Health Data")

    # ====================== DYNAMIC CURRENT YEAR ======================
    if 'Timestamp' in players_df.columns and not players_df.empty:
        temp = players_df.copy()
        temp['RegYear'] = pd.to_datetime(temp['Timestamp'], errors='coerce').dt.year
        current_year = int(temp['RegYear'].max()) if not temp['RegYear'].isna().all() else datetime.datetime.now().year
    else:
        current_year = datetime.datetime.now().year

    # ====================== DANGEROUS DELETE BUTTON ======================
    st.warning("⚠️ **Danger Zone** – Delete data from previous years")
    if st.button("🗑️ Delete ALL Health Information from Previous Years", type="secondary"):
        st.session_state.delete_confirm = True

    if st.session_state.get("delete_confirm"):
        st.error(f"""
        **Are you sure?**  
        This will permanently delete ALL player records from years **before {current_year}**.  
        This action cannot be undone.
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete Previous Years Data", type="primary"):
                # Perform the deletion
                if 'Timestamp' in players_df.columns:
                    players_df['RegYear'] = pd.to_datetime(players_df['Timestamp'], errors='coerce').dt.year
                    players_to_keep = players_df[players_df['RegYear'] == current_year].copy()
                    
                    sheet.worksheet("Players").update(
                        [players_to_keep.columns.values.tolist()] + 
                        players_to_keep.fillna("").values.tolist()
                    )
                    
                    st.success(f"✅ Successfully deleted all data from previous years. Only {current_year} data remains.")
                    st.session_state.delete_confirm = False
                    st.cache_data.clear()
                    st.rerun()
        with col2:
            if st.button("❌ Cancel", type="secondary"):
                st.session_state.delete_confirm = False
                st.rerun()

    # ====================== TEAM SELECTOR ======================
    if can_see_all_teams:
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    else:
        team_options = sorted([t for t in teams_df["TeamName"].dropna().unique().tolist() if t in allowed_teams])

    selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

    # ====================== FILTER ROSTER TO CURRENT YEAR ONLY ======================
    roster = players_df.copy()

    if 'Timestamp' in roster.columns:
        roster['RegYear'] = pd.to_datetime(roster['Timestamp'], errors='coerce').dt.year
        roster = roster[roster['RegYear'] == current_year]

    if selected_team != "All Teams":
        roster = roster[roster.get("Team Assignment", "") == selected_team]

    if roster.empty:
        st.info(f"No players found for the selected team in the {current_year} season.")
        return

    st.subheader(f"Roster for {selected_team} – {current_year} Season")

    # Medical details column lookup
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

    st.caption(f"✅ Restricted Health Data – {current_year} Season Only (auto-detected)")
