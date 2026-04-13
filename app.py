import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v2.7"   # Fixed Medical Alert display on Restricted Health (no raw HTML)

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("RegistrationPortal")
        st.session_state.sheet = sheet

        users_ws = sheet.worksheet("Users")
        user_data = users_ws.get_all_records()
        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip()
            if uname:
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": user.get("password", "changeme123")
                }

        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
    except Exception as e:
        st.error(f"Setup error: {str(e)}")
        st.stop()

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    sheet = st.session_state.sheet

    @st.cache_data(ttl=300)
    def get_worksheet_data(ws_name, expected_headers=None):
        try:
            ws = sheet.worksheet(ws_name)
            if expected_headers:
                data = ws.get_all_records(expected_headers=expected_headers)
            else:
                data = ws.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = pd.Index([f"{col}_{i}" if list(df.columns).count(col) > 1 else col 
                                     for i, col in enumerate(df.columns)])
            return df
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota limit for {ws_name}. Waiting 10 seconds...")
                time.sleep(10)
                return get_worksheet_data(ws_name, expected_headers)
            st.error(f"Error loading {ws_name}: {str(e)}")
            return pd.DataFrame()

    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams", expected_headers=["TeamName", "Division", "Coach"])
    events_df = get_worksheet_data("Events")
    events_reg_df = get_worksheet_data("EventsRegistration")

    def calculate_age_group(dob_str, season_year):
        try:
            dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10"
            elif 11 <= age <= 12: return "U12"
            elif 13 <= age <= 14: return "U14"
            elif 15 <= age <= 16: return "U16"
            return f"Outside {season_year}"
        except:
            return "Invalid"

    if "Date of Birth" in players_df.columns:
        players_df["AgeGroup"] = players_df["Date of Birth"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # User roles
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    # ====================== SIDEBAR ======================
    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")
    st.sidebar.caption(f"**Version:** {VERSION}")

    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("👤 Profile", key="profile_btn", use_container_width=True):
            st.session_state.page = "👤 Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", key="admin_btn", use_container_width=True):
            st.session_state.page = "🔧 Admin"

    if st.sidebar.button("🚪 Logout", key="logout_btn", type="secondary"):
        st.session_state.authenticator.logout('main')
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                if key in st.session_state:
                    del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    # Main Navigation
    if st.sidebar.button("📋 Players", key="nav_players", use_container_width=True):
        st.session_state.page = "📋 Players"
    if st.sidebar.button("📋 Registrar", key="nav_registrar", use_container_width=True):
        st.session_state.page = "📋 Registrar"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if st.sidebar.button("🏕️ Events", key="nav_events", use_container_width=True):
        st.session_state.page = "🏕️ Events"

    if "page" not in st.session_state:
        st.session_state.page = "📋 Players"

    page = st.session_state.page

    # ====================== PAGES ======================
    if page == "📋 Players":
        st.header("Player Roster")
        team_options = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Players"]
        selected_team = st.selectbox("Filter by Team", team_options, key="team_filter")

        if selected_team == "All Players":
            df_display = players_df.copy()
        else:
            df_display = players_df[players_df["Team"] == selected_team].copy()

        display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", "Years Experience", 
                        "ParentName", "ParentPhone", "ParentEmail", "Secondary Emergency Contact Name", "Team", "RegisteredCamps"]
        available_cols = [c for c in display_cols if c in df_display.columns]
        df_display = df_display[available_cols]

        search = st.text_input("🔍 Search players", key="player_search")
        if search:
            df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="player_editor")
        if st.button("💾 Save Player Changes", type="primary"):
            for col in edited.columns:
                players_df[col] = edited[col]
            sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("✅ Saved!")

    elif page == "📋 Registrar":
        st.header("📋 Registrar")

        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2, key="global_season_year")

        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            if st.button("📊 Dashboard", key="reg_dashboard", use_container_width=True):
                st.session_state.reg_subpage = "Dashboard"
        with sub_col2:
            if st.button("👥 Team Assignments", key="reg_assign", use_container_width=True):
                st.session_state.reg_subpage = "Team Assignments"
        with sub_col3:
            if st.button("📅 Event Creation", key="reg_event", use_container_width=True):
                st.session_state.reg_subpage = "Event Creation"

        if "reg_subpage" not in st.session_state:
            st.session_state.reg_subpage = "Dashboard"

        subpage = st.session_state.reg_subpage

        if subpage == "Dashboard":
            st.subheader(f"Registered Players – {selected_year} Season")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1: st.metric("Total Players", len(players_df))
            with col2: st.metric("U10", len(players_df[players_df.get("AgeGroup", "") == "U10"]))
            with col3: st.metric("U12", len(players_df[players_df.get("AgeGroup", "") == "U12"]))
            with col4: st.metric("U14", len(players_df[players_df.get("AgeGroup", "") == "U14"]))
            with col5: st.metric("U16", len(players_df[players_df.get("AgeGroup", "") == "U16"]))

            st.subheader("Current Team Roster Summary")
            if not teams_df.empty and "TeamName" in teams_df.columns:
                team_summary = players_df.groupby("Team")["First Name"].count().reset_index()
                team_summary.columns = ["TeamName", "Players Assigned"]
                team_summary = team_summary.merge(teams_df[["TeamName", "Division"]], on="TeamName", how="left")
                team_summary = team_summary.fillna({"Division": "Unknown"})
                st.dataframe(team_summary[["TeamName", "Division", "Players Assigned"]], use_container_width=True, hide_index=True)
            else:
                st.info("No teams created yet.")

        elif subpage == "Team Assignments":
            st.subheader("👥 Team Assignments")

            if st.button("🔄 Refresh Teams & Players", type="primary"):
                st.cache_data.clear()
                st.rerun()

            show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")

            if show_unassigned:
                available_players = players_df[players_df["Team"].isna() | (players_df["Team"] == "")]
            else:
                available_players = players_df

            player_list = (available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str)).tolist()
            p_sel = st.selectbox("Select Player", player_list, key="assign_player") if player_list else None

            if p_sel:
                idx = available_players.index[available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str) == p_sel][0]
                player_row = players_df.iloc[idx]

                st.subheader("Selected Player")
                with st.container(border=True):
                    colA, colB = st.columns([1, 2])
                    with colA:
                        st.write(f"**{player_row['First Name']} {player_row['Last Name']}**")
                        st.write(f"**DOB:** {player_row.get('Date of Birth', 'N/A')}")
                    with colB:
                        player_age_group = calculate_age_group(player_row.get("Date of Birth"), selected_year)
                        st.write(f"**Age Group:** {player_age_group}")
                        st.write(f"**Weight:** {player_row.get('Weight', 'N/A')}")
                        st.write(f"**Years Experience:** {player_row.get('Years Experience', 'N/A')}")

                st.subheader("Available Teams for this Age Group")
                matching_teams = teams_df[teams_df.get("Division", "").str.strip() == player_age_group]["TeamName"].tolist() if not teams_df.empty else []

                if matching_teams:
                    st.write("**Matching Teams:**", ", ".join(matching_teams))
                else:
                    st.warning(f"No teams currently exist for **{player_age_group}**. Create one below.")

                t_sel = st.selectbox("Assign to Existing Team", matching_teams + ["— Create New Team —"], key="assign_team")

                if t_sel and t_sel != "— Create New Team —":
                    if st.button("Assign Player to Team", key="assign_btn"):
                        players_df.at[idx, "Team"] = t_sel
                        sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                        st.success(f"✅ {p_sel} assigned to {t_sel}!")

                if t_sel == "— Create New Team —":
                    st.subheader("Create New Team")
                    with st.form("new_team_form", clear_on_submit=True):
                        new_team_name = st.text_input("New Team Name", value=f"{player_age_group} Team")
                        new_coach = st.text_input("Coach Name (optional)")
                        submitted = st.form_submit_button("Create Team & Assign Player")
                        if submitted:
                            if new_team_name:
                                new_team_row = {"TeamName": new_team_name, "Division": player_age_group, "Coach": new_coach if new_coach else ""}
                                teams_df = pd.concat([teams_df, pd.DataFrame([new_team_row])], ignore_index=True)
                                sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())

                                players_df.at[idx, "Team"] = new_team_name
                                sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())

                                st.success(f"✅ New team '{new_team_name}' created and {p_sel} assigned!")
                                st.rerun()

        elif subpage == "Event Creation":
            st.subheader("📅 Upcoming & Ongoing Events")

            if st.button("🔄 Refresh Events List", type="primary"):
                st.cache_data.clear()
                st.rerun()

            today = datetime.date.today()
            if not events_df.empty:
                events_display = events_df.copy()

                name_col = next((c for c in ["EventName", "Name"] if c in events_display.columns), None)
                start_col = next((c for c in ["Start Date", "Start"] if c in events_display.columns), None)
                end_col = next((c for c in ["End Date", "End"] if c in events_display.columns), None)

                if name_col and start_col and end_col:
                    def get_status(row):
                        try:
                            end_str = str(row[end_col]).strip()
                            if end_str and end_str.lower() != "nan":
                                end_date = datetime.datetime.strptime(end_str.split()[0], "%Y-%m-%d").date()
                                if end_date < today:
                                    return "Finished"
                            start_str = str(row[start_col]).strip()
                            if start_str and start_str.lower() != "nan":
                                start_date = datetime.datetime.strptime(start_str.split()[0], "%Y-%m-%d").date()
                                if start_date <= today:
                                    return "Ongoing"
                            return "Upcoming"
                        except:
                            return "Unknown"

                    events_display["Status"] = events_display.apply(get_status, axis=1)
                    display_cols = [name_col, start_col, end_col, "Status"]
                    st.dataframe(events_display[display_cols], use_container_width=True)
                else:
                    st.dataframe(events_display, use_container_width=True)
            else:
                st.info("No events created yet.")

            st.subheader("Create New Event")
            if can_rw:
                e_name = st.text_input("Event Name", key="event_name")
                col1, col2 = st.columns(2)
                with col1:
                    e_start_date = st.date_input("Start Date", key="e_start_date")
                    e_start_time = st.time_input("Start Time", key="e_start_time", value=datetime.time(9, 0))
                with col2:
                    e_end_date = st.date_input("End Date", key="e_end_date")
                    e_end_time = st.time_input("End Time", key="e_end_time", value=datetime.time(16, 0))
                e_max = st.number_input("Max Participants", min_value=1, value=40, key="event_max")
                e_location = st.text_input("Location", key="event_location")
                e_desc = st.text_area("Description", key="event_desc")

                if st.button("Create New Event", key="create_event"):
                    new_event = {
                        "EventID": len(events_df) + 1,
                        "EventName": e_name,
                        "Start Date": str(e_start_date),
                        "End Date": str(e_end_date),
                        "Start Time": str(e_start_time),
                        "End Time": str(e_end_time),
                        "Location": e_location,
                        "Description": e_desc,
                        "MaxPlayers": e_max
                    }
                    events_df = pd.concat([events_df, pd.DataFrame([new_event])], ignore_index=True)
                    sheet.worksheet("Events").update([events_df.columns.values.tolist()] + events_df.fillna("").values.tolist())
                    st.success(f"✅ Event '{e_name}' created!")
                    st.rerun()

    elif page == "🔒 Restricted Health":
        if can_restricted:
            st.header("🔒 Restricted Health Data")

            team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
            selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

            if selected_team == "All Teams":
                roster = players_df.copy()
            else:
                roster = players_df[players_df["Team"] == selected_team].copy()

            if not roster.empty:
                st.subheader(f"Roster for {selected_team}")

                for idx, player in roster.iterrows():
                    alerts = []
                    if player.get("History of Concussion") == "Yes": alerts.append("Concussion")
                    if str(player.get("Allergies", "")).strip() not in ["", "nan", "None", "N/A"]: alerts.append("Allergies")
                    if player.get("Epilepsy") == "Yes": alerts.append("Epilepsy")
                    if player.get("Heart Condition") == "Yes": alerts.append("Heart Condition")
                    if player.get("Diabetic") == "Yes": alerts.append("Diabetic")

                    alert_text = " | ".join(alerts) if alerts else ""

                    with st.expander(f"{player['First Name']} {player['Last Name']} {'⚠️ ' + alert_text if alert_text else ''}"):
                        if alert_text:
                            st.error(f"**MEDICAL ALERT:** {alert_text}")
                        st.write(f"**DOB:** {player.get('Date of Birth', 'N/A')}")
                        st.write(f"**Health Number:** {player.get('Health Number', 'N/A')}")
                        st.write(f"**History of Concussion:** {player.get('History of Concussion', 'No')}")
                        st.write(f"**Allergies:** {player.get('Allergies', 'None')}")
                        st.write(f"**Epilepsy:** {player.get('Epilepsy', 'No')}")
                        st.write(f"**Heart Condition:** {player.get('Heart Condition', 'No')}")
                        st.write(f"**Diabetic:** {player.get('Diabetic', 'No')}")
                        st.write(f"**Asthma:** {player.get('Asthma', 'No')}")
                        st.write(f"**Medication:** {player.get('Medication', 'None')}")
                        st.write(f"**Additional Info:** {player.get('AdditionalInfo', 'None')}")
            else:
                st.info("No players found for the selected team.")
        else:
            st.warning("🔒 Restricted access denied.")

    elif page == "🏕️ Events":
        st.header("🏕️ Events – Registered Participants & Check-In")

        if st.button("🔄 Refresh Events & Registrations", type="primary"):
            st.cache_data.clear()
            st.rerun()

        event_name_col = next((col for col in ["EventName", "Name", "Event"] if col in events_df.columns), None)

        if not events_df.empty and event_name_col:
            event_list = events_df[event_name_col].dropna().unique().tolist()
            if event_list:
                selected_event = st.selectbox("Select Event", event_list, key="event_selector")

                if selected_event:
                    reg_event_col = next((col for col in ["EventName", "Name", "Event"] if col in events_reg_df.columns), None)
                    filtered_reg = events_reg_df[events_reg_df[reg_event_col] == selected_event].copy() if reg_event_col else events_reg_df.copy()

                    if not filtered_reg.empty:
                        st.subheader(f"Registrations for: {selected_event}")

                        if "CheckIn" not in filtered_reg.columns:
                            filtered_reg["CheckIn"] = False
                        if "CheckInTime" not in filtered_reg.columns:
                            filtered_reg["CheckInTime"] = ""

                        name_col = next((col for col in ["First Name", "Last Name", "Name", "Player Name"] if col in filtered_reg.columns), None)
                        if name_col and "First Name" in filtered_reg.columns and "Last Name" in filtered_reg.columns:
                            filtered_reg["Player Name"] = filtered_reg["First Name"].astype(str) + " " + filtered_reg["Last Name"].astype(str)

                        edited_reg = st.data_editor(
                            filtered_reg,
                            num_rows="dynamic",
                            use_container_width=True,
                            column_config={
                                "CheckIn": st.column_config.CheckboxColumn("Checked In", default=False, width="small"),
                                "CheckInTime": st.column_config.TextColumn("Check-In Time", disabled=True)
                            },
                            key="events_checkin_editor"
                        )

                        if st.button("💾 Save Check-In Changes", type="primary"):
                            for i, row in edited_reg.iterrows():
                                if row.get("CheckIn") is True and not row.get("CheckInTime"):
                                    edited_reg.at[i, "CheckInTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                            sheet.worksheet("EventsRegistration").update(
                                [edited_reg.columns.values.tolist()] + edited_reg.fillna("").values.tolist()
                            )
                            st.success("✅ Check-in data saved!")
                    else:
                        st.info(f"No registrations yet for '{selected_event}'.")
            else:
                st.info("No events have been created yet.")
        else:
            st.warning("No events found. Please create events in Registrar → Event Creation first.")

    elif page == "🔧 Admin" and is_admin:
        st.header("🔧 Admin – User Management")
        st.info("Full permission editor coming soon.\n\nYou can edit the **Users** sheet directly for now.")

    elif page == "👤 Profile":
        st.header("👤 Profile")
        st.write(f"**Logged in as:** {name} ({username})")
        st.subheader("Change Password")
        with st.form("password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Change Password")
            if submitted:
                if not new_password or new_password != confirm_password:
                    st.error("New passwords do not match or are empty.")
                else:
                    try:
                        hasher = stauth.Hasher()
                        hashed = hasher.hash(new_password)
                        row_num = [u.get("username") for u in user_records].index(username) + 2
                        sheet.worksheet("Users").update_cell(row_num, 4, hashed)
                        st.success("Password changed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
