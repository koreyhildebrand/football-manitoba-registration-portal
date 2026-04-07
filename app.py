import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state or "sheet_loaded" not in st.session_state:
    # Load users from sheet
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open("RegistrationPortal")
        users_ws = sheet.worksheet("Users")
        user_data = users_ws.get_all_records()

        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip()
            if uname:
                pw = str(user.get("password", "changeme123")).strip()
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": pw
                }

        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name="stvital_mustangs_portal",
            key="super_secret_key_2026_mustangs",
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
        st.session_state.sheet_loaded = True
    except Exception as e:
        st.error(f"Setup error: {str(e)}")
        st.stop()

st.session_state.authenticator.login(location='main')

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status is True:
    st.success(f"✅ Logged in as **{name}**")
    st.balloons()
    st.info("Login successful! The full portal is being loaded...")

    # You can add the rest of the app here later
    st.write("### Welcome to St. Vital Mustangs Registration Portal")
    st.write("All features (Players, Registrar, Camps, etc.) will be available in the next update.")

elif authentication_status is False:
    st.error("❌ Invalid username or password")
    st.info("Try:\n**Username:** `admin`\n**Password:** `changeme123`")
else:
    st.warning("Please enter your username and password")

st.caption("St. Vital Mustangs Registration Portal - Login Debug Mode")
