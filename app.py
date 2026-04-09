import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth

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
        st.session_state.authenticator = stauth.Authenticate(
            credentials={"usernames": {}},
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
        # Build credentials from Users tab
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
        st.session_state.authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        st.info("Common fixes:\n1. Share the sheet 'RegistrationPortal' with your service account email as Editor.\n2. Make sure the sheet name is exactly 'RegistrationPortal'.\n3. Reboot the app after sharing.")
        st.stop()

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    sheet = st.session_state.sheet

    def ensure_worksheet(name, headers):
        try:
            return sheet.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            st.info(f"Creating missing worksheet: {name}")
            ws = sheet.add_worksheet(title=name, rows=200, cols=40)
            ws.append_row(headers)
            return ws

    players_ws = ensure_worksheet("Players", ["First Name","Last Name","Date of Birth","Address","Weight","Years Experience","ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name","Secondary Emergency Contact Phone","Secondary Emergency Contact Email","Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo","RegisteredCamps"])
    teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
    users_ws = ensure_worksheet("Users", ["username","name","email","password","roles","permissions"])
    camps_ws = ensure_worksheet("Camps", ["CampID","CampName","Date","Location","Description","MaxPlayers"])
    camp_reg_ws = ensure_worksheet("CampRegistrations", ["CampName","First Name","Last Name","Birthday","Phone Number","Email","Jersey Size","Years Experience","Session Info","Time Slots","CheckIn","CheckInTime","Additional Notes"])

    players_df = pd.DataFrame(players_ws.get_all_records())
    teams_df = pd.DataFrame(teams_ws.get_all_records())
    camps_df = pd.DataFrame(camps_ws.get_all_records())
    camp_reg_df = pd.DataFrame(camp_reg_ws.get_all_records())

    # Dynamic Age Group
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
    user_records = pd.DataFrame(users_ws.get_all_records()).to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    st.sidebar.success(f"👤 {name}")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

    # Navigation
    nav_options = ["📋 Players", "📋 Registrar"]
    if can_restricted: nav_options.append("🔒 Restricted Health")
    nav_options.append("🏕️ Camps")
    if is_admin: nav_options.append("🔧 Admin")
    nav_options.append("👤 Profile")

    page = st.sidebar.radio("Navigation", nav_options, key="sidebar_nav")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticator.logout('main')
        st.rerun()

    # Pages (same as before - abbreviated for brevity, but include your full Registrar with toggle, dynamic team filtering, etc.)
    if page == "📋 Registrar":
        st.header("📋 Registrar Dashboard")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2)
        # ... (keep your existing metrics, Teams management, Assign Player section with toggle and age-based filtering, Camp creation)
        # Use the same Assign Player code from previous versions

    # ... (include the rest of your pages: Players, Restricted Health, Camps, Admin, Profile)

    st.caption("✅ St. Vital Mustangs Registration Portal")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
