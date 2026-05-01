import streamlit as st
import pandas as pd
import datetime


def show_restricted_health(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet, can_see_all_teams: bool, allowed_teams: list):
    st.header("🔒 Restricted Health Data")

    # ====================== DYNAMIC CURRENT YEAR ======================
    if 'Timestamp' in players_df.columns and not players_df.empty:
        temp = players_df.copy()
        temp['RegYear'] = pd.to_datetime(temp['Timestamp'], errors='coerce').dt.year
        current_year = int(temp['RegYear'].max()) if not temp['RegYear'].isna().all() else datetime.datetime.now().year
    else:
        current_year = datetime.datetime.now().year

    # ====================== HEALTH COLUMNS TO CLEAR ======================
    health_columns = [
        "MB Health Number:",
        "Does your player have a History of Concussions?",
        "Does your player wear Glasses/Contact Lenses?",
        "Does your player have Asthma?",
        "Is your player a Diabetic?",
        "Does your player have Allergies?",
        "Does your player have Epilepsy?",
        "Does your player have a Hearing Problem?",
        "Does your player have a Heart Condition?",
        "Does your player take any Medications?",
        "Has your player had Surgery in the last year?",
        "Has your player had Injuries requiring medical attention in the past year?",
        'If you answered "Yes" to any of the above questions please provide details:(List Medications, Allergies etc..)',
        "(*Any medical condition or injury problem should be checked by your physician before participating in a football program), Please list medications"
    ]

    # ====================== DANGEROUS DELETE BUTTON ======================
    st.warning("⚠️ **Danger Zone** – Clear health data from previous years")
    if st.button("🗑️ Clear ALL Health Information from Previous Years", type="secondary"):
        st.session_state.delete_confirm = True

    if st.session_state.get("delete_confirm"):
        st.error(f"""
        **Are you sure?**  
        This will permanently **clear all health/medical columns** for every player from years **before {current_year}**.  
        Player names, weight, birthdate, and team assignments will be preserved.  
        This action cannot be undone.
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Clear Previous Years Health Data", type="primary"):
                # Make a copy to modify
                players_to_update = players_df.copy()

                if 'Timestamp' in players_to_update.columns:
                    players_to_update['RegYear'] = pd.to_datetime(players_to_update['Timestamp'], errors='coerce').dt.year
                    prev_year_mask = players_to_update['RegYear'] < current_year

                    # Safely convert health columns to object/string type first
                    for col in health_columns:
                        if col in players_to_update.columns:
                            players_to_update[col] = players_to_update[col].astype(object)
                            players_to_update.loc[prev_year_mask, col] = ""

                # Write back to sheet
                sheet.worksheet("Players").update(
                    [players_to_update.columns.values.tolist()] + 
                    players_to_update.fillna("").values.tolist()
                )
                
                st.success(f"✅ Health data from previous years has been cleared. Only {current_year} data remains.")
                st.session_state.delete_confirm = False
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("❌ Cancel", type="secondary"):
                st.session_state.delete_confirm = False
                st.rerun()

    # ====================== TEAM SELECTOR & ROSTER ======================
    if can_see_all_teams:
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    else:
        team_options = sorted([t for t in teams_df["TeamName"].dropna().unique().tolist() if t in allowed_teams])

    selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

    # Filter to current year only
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
