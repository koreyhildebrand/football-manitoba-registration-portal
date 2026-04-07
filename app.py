import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== LOAD SHEET & USERS ======================
@st.cache_resource
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("RegistrationPortal")

sheet = get_gsheet()
users_ws = sheet.worksheet("Users")
user_data = users_ws.get_all_records()

# Build credentials and auto-hash plain passwords
credentials = {"usernames": {}}
updated = False

for i, user in enumerate(user_data):
    uname = str(user.get("username", "")).strip()
    if not uname:
        continue
        
    password = str(user.get("password", "changeme123")).strip()
    
    # Auto-hash if it's still plain text
    if not password.startswith("$2b$") and password != "":
        try:
            hasher = stauth.Hasher([password])
            hashed_pw = hasher.generate()[0]
            # Update the sheet with hashed password
            users_ws.update_cell(i + 2, 4, hashed_pw)  # Column D = password
            password = hashed_pw
            updated = True
        except:
            pass  # Skip if hashing fails

    credentials["usernames"][uname] = {
        "name": user.get("name", uname),
        "email": user.get("email", ""),
        "password": password
    }

if "authenticator" not in st.session_state:
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="stvital_mustangs_portal",
        key="super_secret_key_2026_mustangs",
        cookie_expiry_days=30,
    )
    st.session_state.authenticator = authenticator

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    st.success(f"✅ Logged in successfully as **{name}**")
    st.info("Login is working! The full portal will be loaded in the next step.")

elif authentication_status is False:
    st.error("❌ Invalid username or password")
    st.info("Try: **admin** / **changeme123**")
else:
    st.warning("Please enter your username and password")

st.caption("St. Vital Mustangs Registration Portal - Login Fixed")