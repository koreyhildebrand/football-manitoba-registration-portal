import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit_authenticator as stauth
import datetime
from utils.sheets import get_worksheet_data, get_live_equipment
from pages.equipment import show_equipment
# Import your other page functions here as you add them
# from pages.registrar import show_registrar
# from pages.admin import show_admin
# etc.

# ====================== VERSION CONTROL ======================
VERSION = "v4.01"  # Equipment page fully updated

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

        # Load users for authentication
        users_ws = sheet.worksheet("Users")
        user_data = users_ws.get_all_records()
        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip()
            if uname:
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": user.get("password", "")
                }

        authenticator = stauth.Authenticate(
            credentials,
            cookie_name="mustangs_registration",
            cookie_key=st.secrets["cookie"]["key"],   # Make sure this exists in your secrets
            cookie_expiry_days=30,
        )
        st.session_state.authenticator = authenticator
    except Exception as e:
        st.error(f"Failed to load authentication: {e}")
        st.stop()

authenticator = st.session_state.authenticator
name, authentication_status, username = authenticator.login(location='main')

if authentication_status:
    st.sidebar.success(f"Welcome, {name}!")
    
    # ====================== LOAD DATA ======================
    players_df = get_worksheet_data("Players")
    teams_df   = get_worksheet_data("Teams")

    # ====================== SIDEBAR NAVIGATION ======================
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Equipment Management", "Registrar Dashboard", "Coach Portal", "Football Operations", "Admin", "Profile"],
        key="main_page"
    )

    # ====================== PAGE ROUTING ======================
    if page == "Equipment Management":
        show_equipment(players_df, teams_df, st.session_state.sheet)
    
    elif page == "Registrar Dashboard":
        st.write("👷 Registrar Dashboard – coming soon (or call your function here)")
        # from pages.registrar import show_registrar
        # show_registrar(players_df, teams_df, st.session_state.sheet)
    
    elif page == "Coach Portal":
        st.write("👷 Coach Portal – coming soon")
    
    elif page == "Football Operations":
        st.write("👷 Football Operations – coming soon")
        # from pages.football_operations import show_football_operations
        # show_football_operations(teams_df, st.session_state.sheet, is_admin=False)
    
    elif page == "Admin":
        st.write("👷 Admin – coming soon")
        # from pages.admin import show_admin
        # show_admin(st.session_state.sheet)
    
    elif page == "Profile":
        authenticator.logout(location='sidebar')
        st.write("Profile page – coming soon")

    st.sidebar.caption(f"✅ Version {VERSION}")

elif authentication_status is False:
    st.error("❌ Invalid username or password")
elif authentication_status is None:
    st.warning("Please enter your username and password")

st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")
