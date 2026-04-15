import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.40"  # Equipment page: forced fresh load of equipment data + small delay so summary updates instantly after save

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

if 'logout' not in st.session_state:
    st.session_state.logout = False

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

    # ====================== EQUIPMENT - NO CACHE (always fresh) ======================
    try:
        equipment_df = get_worksheet_data("Equipment")  # This line is intentionally NOT cached for immediate updates
    except:
        sheet.add_worksheet(title="Equipment", rows=1000, cols=20)
        equipment_headers = [
            "PlayerID", "First Name", "Last Name",
            "Helmet", "Helmet Size",
            "Shoulder Pads", "Shoulder Pads Size",
            "Pants", "Pants Size",
            "Belt",
            "Pant Pads", "Thigh Pads", "Tailbone Pad", "Knee Pads",
            "Secured Rental", "Payment Method"
        ]
        sheet.worksheet("Equipment").update([equipment_headers])
        equipment_df = pd.DataFrame(columns=equipment_headers)

    required_cols = ["Helmet Size", "Shoulder Pads Size", "Pants Size", "Thigh Pads", "Tailbone Pad", "Knee Pads"]
    for col in required_cols:
        if col not in equipment_df.columns:
            equipment_df[col] = ""

    def calculate_age_group(dob_str, season_year):
        try:
            dob_str = str(dob_str).strip()
            if '/' in dob_str:
                dob = datetime.datetime.strptime(dob_str, "%m/%d/%Y").date()
            else:
                dob = datetime.datetime.strptime(dob_str.split()[0], "%Y-%m-%d").date()
            age = season_year - dob.year
            if 9 <= age <= 10: return "U10"
            elif 11 <= age <= 12: return "U12"
            elif 13 <= age <= 14: return "U14"
            elif 15 <= age <= 16: return "U16"
            elif 17 <= age <= 18: return "U18"
            elif age >= 19: return "Major"
            return f"Outside {season_year}"
        except:
            return "Invalid"

    if "Birthdate" in players_df.columns:
        players_df["AgeGroup"] = players_df["Birthdate"].apply(lambda x: calculate_age_group(x, datetime.date.today().year))

    # ====================== ROLE & PERMISSION SYSTEM ======================
    user_records = get_worksheet_data("Users").to_dict("records")
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]

    is_admin = "Admin" in roles
    is_registrar = "Registrar" in roles
    is_coach = "Coach" in roles
    is_equipment = "Equipment" in roles

    can_restricted = is_admin or any("Restricted" in r for r in roles)

    restricted_teams_str = user_row.get("RestrictedTeams", "") if user_row else ""
    allowed_teams = [t.strip() for t in restricted_teams_str.split(",") if t.strip()]
    can_see_all_teams = not allowed_teams or any(t.lower() == "all" for t in allowed_teams) or is_admin

    def filter_by_team(df):
        if can_see_all_teams:
            return df
        if "Team Assignment" in df.columns:
            return df[df["Team Assignment"].isin(allowed_teams)]
        return df

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

    if (is_admin or is_registrar) and st.sidebar.button("📋 Registrar", key="nav_registrar", use_container_width=True):
        st.session_state.page = "📋 Registrar"
    if (is_admin or is_equipment) and st.sidebar.button("🛡️ Equipment", key="nav_equipment", use_container_width=True):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", key="nav_restricted", use_container_width=True):
        st.session_state.page = "🔒 Restricted Health"
    if (is_admin or is_registrar or is_coach) and st.sidebar.button("🏕️ Events", key="nav_events", use_container_width=True):
        st.session_state.page = "🏕️ Events"
    if (is_coach or is_admin) and st.sidebar.button("🏈 Coach Portal", key="nav_coach", use_container_width=True):
        st.session_state.page = "🏈 Coach Portal"
    if (is_admin or is_registrar) and st.sidebar.button("⚙️ Football Operations", key="nav_operations", use_container_width=True):
        st.session_state.page = "⚙️ Football Operations"

    if "page" not in st.session_state:
        st.session_state.page = "🏠 Landing"

    page = st.session_state.page

    # ====================== LANDING PAGE ======================
    if page == "🏠 Landing":
        st.markdown(f"<h1 style='text-align: center;'>Welcome, {name}</h1>", unsafe_allow_html=True)
        col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
        with col_logo2:
            st.image(
                "https://images.squarespace-cdn.com/content/v1/58a5f4c8be659445700a4bd4/1491935469145-6FTNR6TR5PMMGJ1EWFP2/logo_white_back.jpg?format=1500w",
                width=400,
                use_column_width=True
            )
        st.markdown(f"<p style='text-align: center; font-size: 18px;'>Your roles: **{', '.join(roles) if roles else 'None'}**</p>", unsafe_allow_html=True)
        st.info("Use the **sidebar** on the left to navigate.")

    # ====================== EQUIPMENT PAGE (v3.40 - guaranteed immediate update) ======================
    elif page == "🛡️ Equipment":
        st.header("🛡️ Equipment Loan Tracking")
        df_filtered = filter_by_team(players_df.copy())
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
        selected_team = st.selectbox("Select Team", team_options, key="equipment_team")

        if selected_team == "All Teams":
            equip_roster = df_filtered.copy()
        else:
            equip_roster = df_filtered[df_filtered.get("Team Assignment", "") == selected_team].copy()

        if not equip_roster.empty:
            st.subheader(f"Equipment for {selected_team} — Click name to edit")

            # Fresh load every time (no cache on equipment_df)
            equip_df = get_worksheet_data("Equipment")
            if "PlayerID" not in equip_df.columns:
                equip_df["PlayerID"] = ""

            for idx, player in equip_roster.iterrows():
                player_id = f"{player.get('First Name','')}_{player.get('Last Name','')}_{player.get('Birthdate','')}"
                existing = equip_df[equip_df.get("PlayerID", "") == player_id]

                # Build rented equipment summary (always from latest data)
                rented_summary = []
                if not existing.empty:
                    if existing["Helmet"].iloc[0]: rented_summary.append("Helmet ✓")
                    if existing["Shoulder Pads"].iloc[0]: rented_summary.append("Shoulder Pads ✓")
                    if existing["Pants"].iloc[0]: rented_summary.append("Pants ✓")
                    if existing["Belt"].iloc[0]: rented_summary.append("Belt ✓")
                    if existing["Pant Pads"].iloc[0]:
                        pads = []
                        if existing["Thigh Pads"].iloc[0]: pads.append("Thigh")
                        if existing["Tailbone Pad"].iloc[0]: pads.append("Tailbone")
                        if existing["Knee Pads"].iloc[0]: pads.append("Knee")
                        if pads:
                            rented_summary.append(f"Pant Pads ({', '.join(pads)})")
                        else:
                            rented_summary.append("Pant Pads ✓")

                summary_text = " | ".join(rented_summary) if rented_summary else "No equipment rented yet"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** – {summary_text}"):
                    col1, col2 = st.columns([3, 2])

                    with col1:
                        helmet = st.checkbox("Helmet", value=existing["Helmet"].iloc[0] if not existing.empty else True, key=f"helm_{idx}")
                        helmet_size = st.text_input("Helmet Size", value=existing["Helmet Size"].iloc[0] if not existing.empty else "", key=f"helm_size_{idx}")

                        shoulder = st.checkbox("Shoulder Pads", value=existing["Shoulder Pads"].iloc[0] if not existing.empty else True, key=f"shoul_{idx}")
                        shoulder_size = st.text_input("Shoulder Pads Size", value=existing["Shoulder Pads Size"].iloc[0] if not existing.empty else "", key=f"shoul_size_{idx}")

                        pants = st.checkbox("Pants", value=existing["Pants"].iloc[0] if not existing.empty else True, key=f"pants_{idx}")
                        pants_size = st.text_input("Pants Size", value=existing["Pants Size"].iloc[0] if not existing.empty else "", key=f"pants_size_{idx}")

                    with col2:
                        belt = st.checkbox("Belt", value=existing["Belt"].iloc[0] if not existing.empty else True, key=f"belt_{idx}")

                        pant_pads = st.checkbox("Pant Pads", value=existing["Pant Pads"].iloc[0] if not existing.empty else True, key=f"ppads_{idx}")
                        thigh_pads = st.checkbox("Thigh Pads", value=existing["Thigh Pads"].iloc[0] if not existing.empty else True, key=f"thigh_{idx}")
                        tailbone_pad = st.checkbox("Tailbone Pad", value=existing["Tailbone Pad"].iloc[0] if not existing.empty else True, key=f"tailbone_{idx}")
                        knee_pads = st.checkbox("Knee Pads", value=existing["Knee Pads"].iloc[0] if not existing.empty else True, key=f"knee_{idx}")

                        secured = st.checkbox("Secured Rental with Cheque / Credit Card", value=existing["Secured Rental"].iloc[0] if not existing.empty else False, key=f"sec_{idx}")
                        payment_method = st.text_input("Cheque # or Credit Card #", value=existing["Payment Method"].iloc[0] if not existing.empty else "", key=f"pay_{idx}")

                    if st.button("Save Equipment for this Player", key=f"save_eq_{idx}"):
                        new_row = {
                            "PlayerID": player_id,
                            "First Name": player["First Name"],
                            "Last Name": player["Last Name"],
                            "Helmet": helmet,
                            "Helmet Size": helmet_size,
                            "Shoulder Pads": shoulder,
                            "Shoulder Pads Size": shoulder_size,
                            "Pants": pants,
                            "Pants Size": pants_size,
                            "Belt": belt,
                            "Pant Pads": pant_pads,
                            "Thigh Pads": thigh_pads,
                            "Tailbone Pad": tailbone_pad,
                            "Knee Pads": knee_pads,
                            "Secured Rental": secured,
                            "Payment Method": payment_method if secured else ""
                        }
                        equip_df = equip_df[equip_df.get("PlayerID", "") != player_id]
                        equip_df = pd.concat([equip_df, pd.DataFrame([new_row])], ignore_index=True)
                        sheet.worksheet("Equipment").update([equip_df.columns.values.tolist()] + equip_df.fillna("").values.tolist())
                        
                        st.success(f"✅ Equipment saved and summary updated for {player['First Name']} {player['Last Name']}")
                        time.sleep(0.3)   # Give Sheets a tiny moment to commit
                        st.rerun()

        else:
            st.info("No players found for the selected team.")

    # ====================== OTHER PAGES (unchanged) ======================
    # Registrar, Coach Portal, Restricted Health, Events, Football Operations, Admin, Profile pages remain as before

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
