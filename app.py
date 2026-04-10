import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

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

# Safe login call - protect against missing 'logout' key
try:
    st.session_state.authenticator.login(location='main')
except KeyError as e:
    if "logout" in str(e):
        # Clean up leftover logout flag
        if 'logout' in st.session_state:
            del st.session_state['logout']
        st.session_state.authenticator.login(location='main')
    else:
        raise

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    sheet = st.session_state.sheet

    @st.cache_data(ttl=300)
    def get_worksheet_data(ws_name):
        try:
            ws = sheet.worksheet(ws_name)
            return pd.DataFrame(ws.get_all_records())
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Quota limit for {ws_name}. Waiting 10 seconds...")
                time.sleep(10)
                ws = sheet.worksheet(ws_name)
                return pd.DataFrame(ws.get_all_records())
            st.error(f"Error loading {ws_name}: {str(e)}")
            return pd.DataFrame()

    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams")
    camps_df = get_worksheet_data("Camps")
    camp_reg_df = get_worksheet_data("CampRegistrations")

    def calculate_age_group(dob_str, season_year):
        try:
            dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10 Cruncher"
            elif 11 <= age <= 12: return "U12 Atom"
            elif 13 <= age <= 14: return "U14 PeeWee"
            elif 15 <= age <= 16: return "U16 Bantam"
            return f"Outside {season_year} Eligibility"
        except:
            return "Invalid DOB"

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

    # ====================== SIDEBAR - BUTTONS ABOVE NAV ======================
    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

    # Profile, Admin, Logout - ABOVE Navigation
    col1, col2 = st.sidebar.columns([1, 1])
    with col1:
        if st.button("👤 Profile", key="profile_btn", use_container_width=True):
            st.session_state.page = "👤 Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", key="admin_btn", use_container_width=True):
            st.session_state.page = "🔧 Admin"

    if st.sidebar.button("🚪 Logout", key="logout_btn", type="secondary"):
        try:
            st.session_state.authenticator.logout('main')
        except:
            pass
        # Safe clear - only remove non-auth keys
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                if key in st.session_state:
                    del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    # Main Navigation - All as buttons
    if st.sidebar.button("📋 Players", key="nav_players", use_container_width=True):
        st.session_state.page = "📋 Players"
    if st.sidebar.button("📋 Registrar", key="nav_registrar", use_container_width=True):
        st.session_state.page = "📋 Registrar"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if st.sidebar.button("🏕️ Camps", key="nav_camps", use_container_width=True):
        st.session_state.page = "🏕️ Camps"

    # Default page
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
        st.header("📋 Registrar Dashboard")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2)

        st.subheader(f"Registered Players – {selected_year} Season")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.metric("Total Players", len(players_df))
        with col2: st.metric("U10 Cruncher", len(players_df[players_df.get("AgeGroup", "") == "U10 Cruncher"]))
        with col3: st.metric("U12 Atom", len(players_df[players_df.get("AgeGroup", "") == "U12 Atom"]))
        with col4: st.metric("U14 PeeWee", len(players_df[players_df.get("AgeGroup", "") == "U14 PeeWee"]))
        with col5: st.metric("U16 Bantam", len(players_df[players_df.get("AgeGroup", "") == "U16 Bantam"]))

        st.subheader("Teams & Coaches Management")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
            if st.button("💾 Save Teams Changes"):
                try:
                    sheet.worksheet("Teams").update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                    st.success("✅ Teams saved!")
                except Exception as e:
                    st.error(f"Save failed: {str(e)}")

        st.subheader("Assign Player to Team")
        show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")

        if show_unassigned:
            available_players = players_df[players_df["Team"].isna() | (players_df["Team"] == "")]
        else:
            available_players = players_df

        player_list = (available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str)).tolist()
        p_sel = st.selectbox("Select Player", player_list, key="assign_player") if player_list else None

        if p_sel:
            idx = available_players.index[available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str) == p_sel][0]
            player_dob = players_df.at[idx, "Date of Birth"]
            player_age_group = calculate_age_group(player_dob, selected_year)

            matching_teams = teams_df[teams_df["Division"] == player_age_group]["TeamName"].tolist() if not teams_df.empty else ["No matching teams"]

            t_sel = st.selectbox("Assign to Team (matching age group)", matching_teams, key="assign_team")

            if st.button("Assign Player to Team", key="assign_btn") and p_sel and t_sel:
                players_df.at[idx, "Team"] = t_sel
                sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success(f"✅ {p_sel} assigned to {t_sel}!")

        # Camp Session Creation with Start/End Date & Time
        st.subheader("Create New Camp Session")
        if can_rw:
            col1, col2 = st.columns(2)
            with col1:
                c_name = st.text_input("Camp Name", key="camp_name")
                c_start_date = st.date_input("Start Date", key="c_start_date")
                c_start_time = st.time_input("Start Time", key="c_start_time", value=datetime.time(9, 0))
            with col2:
                c_end_date = st.date_input("End Date", key="c_end_date")
                c_end_time = st.time_input("End Time", key="c_end_time", value=datetime.time(16, 0))
                c_max = st.number_input("Max Players", min_value=1, value=40, key="camp_max")
            c_location = st.text_input("Location", key="camp_location")
            c_desc = st.text_area("Description", key="camp_desc")

            if st.button("Create Camp Session", key="create_camp"):
                new_camp = {
                    "CampID": len(camps_df) + 1,
                    "CampName": c_name,
                    "Start Date": str(c_start_date),
                    "End Date": str(c_end_date),
                    "Start Time": str(c_start_time),
                    "End Time": str(c_end_time),
                    "Location": c_location,
                    "Description": c_desc,
                    "MaxPlayers": c_max
                }
                camps_df = pd.concat([camps_df, pd.DataFrame([new_camp])], ignore_index=True)
                sheet.worksheet("Camps").update([camps_df.columns.values.tolist()] + camps_df.fillna("").values.tolist())
                st.success(f"✅ Camp '{c_name}' created!")

    elif page == "🔒 Restricted Health":
        if can_restricted:
            st.header("🔒 Restricted Health Data")
            health_cols = ["First Name","Last Name","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo"]
            avail = [c for c in health_cols if c in players_df.columns]
            edited_h = st.data_editor(players_df[avail], num_rows="dynamic", use_container_width=True, key="health_editor")
            if st.button("💾 Save Restricted Data"):
                for c in edited_h.columns:
                    players_df[c] = edited_h[c]
                sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("🔒 Saved securely!")
        else:
            st.warning("🔒 Restricted access denied.")

    elif page == "🏕️ Camps":
        st.header("🏕️ Camps – Registered Players & Check-In")
        if not camp_reg_df.empty:
            edited_camp_reg = st.data_editor(camp_reg_df, num_rows="dynamic", use_container_width=True, key="camp_reg_editor")
            if st.button("💾 Save Check-In Changes"):
                sheet.worksheet("CampRegistrations").update([edited_camp_reg.columns.values.tolist()] + edited_camp_reg.fillna("").values.tolist())
                st.success("✅ Check-in data saved!")
        else:
            st.info("No camp registrations yet.")

        st.subheader("Drill Down to Attendee")
        if not camp_reg_df.empty:
            attendee_list = (camp_reg_df["First Name"].astype(str) + " " + camp_reg_df["Last Name"].astype(str)).tolist()
            selected_attendee = st.selectbox("Select Attendee", attendee_list, key="attendee_select")
            if selected_attendee:
                idx = attendee_list.index(selected_attendee)
                attendee_data = camp_reg_df.iloc[idx]
                st.json(attendee_data.to_dict())

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

    st.caption("✅ St. Vital Mustangs Registration Portal")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
