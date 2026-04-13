import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.6"   # Fixed double login call that caused TypeError

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== AUTHENTICATION SETUP ======================
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

# Single login call
name, authentication_status, username = st.session_state.authenticator.login(location='main')

if authentication_status is True:
    # ====================== RECORD SUCCESSFUL LOGIN ======================
    try:
        log_ws = st.session_state.sheet.worksheet("LoginLog")
    except gspread.exceptions.WorksheetNotFound:
        log_ws = st.session_state.sheet.add_worksheet(title="LoginLog", rows=1000, cols=5)
        log_ws.update([["Timestamp", "Username", "Name", "Success"]])

    log_entry = [[datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, name, "True"]]
    log_ws.append_rows(log_entry)

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

    # Ensure Equipment sheet exists
    try:
        equipment_df = get_worksheet_data("Equipment")
    except:
        sheet.add_worksheet(title="Equipment", rows=1000, cols=10)
        equipment_headers = ["PlayerID", "First Name", "Last Name", "Helmet", "Shoulder Pads", "Pants", "Belt", "Pant Pads", "Secured Rental", "Payment Method"]
        sheet.worksheet("Equipment").update([equipment_headers])
        equipment_df = pd.DataFrame(columns=equipment_headers)

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
    if st.sidebar.button("🛡️ Equipment", key="nav_equipment", use_container_width=True):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if st.sidebar.button("🏕️ Events", key="nav_events", use_container_width=True):
        st.session_state.page = "🏕️ Events"

    if "page" not in st.session_state:
        st.session_state.page = "📋 Players"

    page = st.session_state.page

    # ====================== PAGES ======================
    # (All your existing pages remain exactly the same — Players, Registrar, Equipment, Restricted Health, Events, Admin, Profile)

    if page == "📋 Players":
        # ... (same as before)
        st.header("Player Roster")
        # [full Players code unchanged]

    elif page == "📋 Registrar":
        # [full Registrar code unchanged]

    elif page == "🛡️ Equipment":
        # [full Equipment code unchanged]

    elif page == "🔒 Restricted Health":
        # [full Restricted Health code unchanged]

    elif page == "🏕️ Events":
        # [full Events code unchanged]

    elif page == "🔧 Admin" and is_admin:
        st.header("🔧 Admin – User Management")
        # [full user management code unchanged]

        # Sign-in Log
        st.subheader("📜 Sign-in Log")
        if st.button("Show Sign-in Log", type="primary"):
            log_df = get_worksheet_data("LoginLog")
            if not log_df.empty:
                st.dataframe(log_df.sort_values(by="Timestamp", ascending=False), width="stretch", hide_index=True)
            else:
                st.info("No login records yet.")

    elif page == "👤 Profile":
        # [full Profile code unchanged]

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
