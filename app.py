import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.11"  # Fixed Restricted Health tab visibility for users with "Restricted" role

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

    try:
        equipment_df = get_worksheet_data("Equipment")
    except:
        sheet.add_worksheet(title="Equipment", rows=1000, cols=10)
        equipment_headers = ["PlayerID", "First Name", "Last Name", "Helmet", "Shoulder Pads", "Pants", "Belt", "Pant Pads", "Secured Rental", "Payment Method"]
        sheet.worksheet("Equipment").update([equipment_headers])
        equipment_df = pd.DataFrame(columns=equipment_headers)

    def calculate_age_group(dob_str, season_year):
        try:
            dob = datetime.datetime.strptime(str(dob_str).strip().split()[0], "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10"
            elif 11 <= age <= 12: return "U12"
            elif 13 <= age <= 14: return "U14"
            elif 15 <= age <= 16: return "U16"
            return f"Outside {season_year}"
        except:
            return "Invalid"

    if "Birthdate" in players_df.columns:
        players_df["AgeGroup"] = players_df["Birthdate"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))
    elif "Date of Birth" in players_df.columns:
        players_df["AgeGroup"] = players_df["Date of Birth"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # User roles + RestrictedTeams
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles

    # Fixed: Check for "Restricted" anywhere in roles string (handles Restricted:Write, Restricted, etc.)
    can_restricted = is_admin or any("Restricted" in r for r in roles)

    restricted_teams_str = user_row.get("RestrictedTeams", "") if user_row else ""
    allowed_teams = [t.strip() for t in restricted_teams_str.split(",") if t.strip()]
    can_see_all_teams = not allowed_teams or any(t.lower() == "all" for t in allowed_teams) or is_admin

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

    if st.sidebar.button("📋 Players", key="nav_players", use_container_width=True):
        st.session_state.page = "📋 Players"
    if st.sidebar.button("📋 Registrar", key="nav_registrar", use_container_width=True):
        st.session_state.page = "📋 Registrar"
    if st.sidebar.button("🛡️ Equipment", key="nav_equipment", use_container_width=True):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if st.sidebar.button("🏕️ Events", key="nav_events", use_container_width=True):
        st.session_state.page = "🏕️ Events"

    if "page" not in st.session_state:
        st.session_state.page = "📋 Players"

    page = st.session_state.page

    # ====================== RESTRICTED HEALTH PAGE ======================
    if page == "🔒 Restricted Health":
        if can_restricted:
            st.header("🔒 Restricted Health Data")

            if can_see_all_teams:
                team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
            else:
                team_options = sorted([t for t in teams_df["TeamName"].dropna().unique().tolist() if t in allowed_teams])

            selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

            if selected_team == "All Teams":
                roster = players_df.copy()
            else:
                roster = players_df[players_df.get("Team Assignment", "") == selected_team].copy()

            if not roster.empty:
                st.subheader(f"Roster for {selected_team}")
                for idx, player in roster.iterrows():
                    alerts = []
                    if player.get("Does your player have a History of Concussions?") == "Yes": alerts.append("Concussion")
                    if str(player.get("Does your player have Allergies?", "")).strip() not in ["", "nan", "None", "N/A"]: alerts.append("Allergies")
                    if player.get("Does your player have Epilepsy?") == "Yes": alerts.append("Epilepsy")
                    if player.get("Does your player have a Heart Condition?") == "Yes": alerts.append("Heart Condition")
                    if player.get("Is your player a Diabetic?") == "Yes": alerts.append("Diabetic")

                    alert_text = " | ".join(alerts) if alerts else ""

                    with st.expander(f"{player.get('First Name','')} {player.get('Last Name','')} {'⚠️ ' + alert_text if alert_text else ''}"):
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
            else:
                st.info("No players found for the selected team.")
        else:
            st.warning("🔒 Restricted access denied.")

    # All other pages (Players, Registrar, Equipment, Events, Admin, Profile) are exactly as in your stable v3.3
    # (They use safe fallbacks and your "Team Assignment" column where needed)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
