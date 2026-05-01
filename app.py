import streamlit as st
import pandas as pd

# ====================== CONFIG ======================
from config import VERSION, PAGE_ICON, TITLE

# Hide the automatic multi-page navigation list
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title=TITLE, layout="wide", page_icon=PAGE_ICON)
st.title(f"🏈 {TITLE}")

# ====================== FIX FOR LOGOUT ERROR ======================
if 'logout' not in st.session_state:
    st.session_state.logout = False

# ====================== AUTHENTICATION ======================
from utils.auth import initialize_authenticator
authenticator = initialize_authenticator()
authenticator.login(location='main')

if st.session_state.get('authentication_status') is True:
    name = st.session_state.name
    username = st.session_state.username
    sheet = st.session_state.sheet

    # ====================== LOAD CORE DATA ======================
    from utils.sheets import get_worksheet_data
    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams")
    events_df = get_worksheet_data("Events")
    events_reg_df = get_worksheet_data("EventsRegistration")

    # ====================== ROLE SYSTEM ======================
    from utils.helpers import filter_by_team
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    is_registrar = "Registrar" in roles
    is_coach = "Coach" in roles
    is_equipment_role = "Equipment" in roles
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
        if st.button("👤 Profile", width='stretch'):
            st.session_state.page = "Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", width='stretch'):
            st.session_state.page = "Admin"

    if st.sidebar.button("🚪 Logout", type="secondary"):
        authenticator.logout('main')
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    # ====================== NEW SIDEBAR ORDER ======================
    if (is_coach or is_admin) and st.sidebar.button("🏈 Coach Portal", width='stretch'):
        st.session_state.page = "Coach Portal"
    if (is_admin or is_registrar or is_coach) and st.sidebar.button("🏕️ Events", width='stretch'):
        st.session_state.page = "Events"
    if (is_admin or is_equipment_role) and st.sidebar.button("🛡️ Equipment", width='stretch'):
        st.session_state.page = "Equipment"
    if (is_admin or is_registrar) and st.sidebar.button("📋 Registrar", width='stretch'):
        st.session_state.page = "Registrar"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", width='stretch'):
        st.session_state.page = "Restricted Health"

    if "page" not in st.session_state:
        st.session_state.page = "Landing"

    # ====================== PAGE ROUTING ======================
    page = st.session_state.page
    if page == "Landing":
        from pages.landing import show_landing
        show_landing(name)
    elif page == "Equipment":
        from pages.equipment import show_equipment
        show_equipment(players_df, teams_df, sheet)
    elif page == "Registrar":
        from pages.registrar import show_registrar
        show_registrar(players_df, teams_df, sheet, events_df, can_see_all_teams, allowed_teams)
    elif page == "Coach Portal":
        from pages.coach_portal import show_coach_portal
        show_coach_portal(players_df, teams_df, name, is_admin)
    elif page == "Restricted Health":
        from pages.restricted_health import show_restricted_health
        show_restricted_health(players_df, teams_df, can_see_all_teams, allowed_teams)
    elif page == "Events":
        from pages.events import show_events
        show_events(sheet)
    elif page == "Admin" and is_admin:
        from pages.admin import show_admin
        show_admin(sheet)
    elif page == "Profile":
        from pages.profile import show_profile
        show_profile(user_row, sheet, username, name)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if st.session_state.get('authentication_status') is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
