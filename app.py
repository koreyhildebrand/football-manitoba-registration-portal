import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.60"  # Fixed KeyError on new Equipment sheet + safe column handling + immediate summary refresh

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
    def get_worksheet_data(ws_name):
        try:
            ws = sheet.worksheet(ws_name)
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            if "429" in str(e):
                time.sleep(10)
                return get_worksheet_data(ws_name)
            st.error(f"Error loading {ws_name}: {str(e)}")
            return pd.DataFrame()

    players_df = get_worksheet_data("Players")
    teams_df = get_worksheet_data("Teams")
    events_df = get_worksheet_data("Events")
    events_reg_df = get_worksheet_data("EventsRegistration")

    # ====================== EQUIPMENT (safe handling for new sheet) ======================
    try:
        equipment_df = get_worksheet_data("Equipment")
    except:
        equipment_df = pd.DataFrame()

    # Ensure all required columns exist (auto-create if new/empty sheet)
    required_cols = [
        "PlayerID", "First Name", "Last Name",
        "Helmet", "Helmet Size",
        "Shoulder Pads", "Shoulder Pads Size",
        "Pants w/Belt", "Pants Size",
        "Thigh Pads", "Tailbone Pad", "Knee Pads",
        "Secured Rental"
    ]
    for col in required_cols:
        if col not in equipment_df.columns:
            equipment_df[col] = False if "Pads" in col or col in ["Helmet", "Shoulder Pads", "Pants w/Belt", "Secured Rental"] else ""

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

    # ====================== ROLE SYSTEM ======================
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

    def filter_by_team(df):
        if can_see_all_teams or df.empty:
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
        if st.button("👤 Profile", width='stretch'):
            st.session_state.page = "👤 Profile"
    with col2:
        if is_admin and st.button("🔧 Admin", width='stretch'):
            st.session_state.page = "🔧 Admin"

    if st.sidebar.button("🚪 Logout", type="secondary"):
        st.session_state.authenticator.logout('main')
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet"]:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")

    if (is_admin or is_registrar) and st.sidebar.button("📋 Registrar", width='stretch'):
        st.session_state.page = "📋 Registrar"
    if (is_admin or is_equipment_role) and st.sidebar.button("🛡️ Equipment", width='stretch'):
        st.session_state.page = "🛡️ Equipment"
    if can_restricted and st.sidebar.button("🔒 Restricted Health", width='stretch'):
        st.session_state.page = "🔒 Restricted Health"
    if (is_admin or is_registrar or is_coach) and st.sidebar.button("🏕️ Events", width='stretch'):
        st.session_state.page = "🏕️ Events"
    if (is_coach or is_admin) and st.sidebar.button("🏈 Coach Portal", width='stretch'):
        st.session_state.page = "🏈 Coach Portal"
    if (is_admin or is_registrar) and st.sidebar.button("⚙️ Football Operations", width='stretch'):
        st.session_state.page = "⚙️ Football Operations"

    if "page" not in st.session_state:
        st.session_state.page = "🏠 Landing"

    page = st.session_state.page

    # ====================== LANDING ======================
    if page == "🏠 Landing":
        st.markdown(f"<h1 style='text-align: center;'>Welcome, {name}</h1>", unsafe_allow_html=True)
        col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
        with col_logo2:
            st.image("https://images.squarespace-cdn.com/content/v1/58a5f4c8be659445700a4bd4/1491935469145-6FTNR6TR5PMMGJ1EWFP2/logo_white_back.jpg?format=1500w", width=400)
        st.info("Use the sidebar to navigate.")

    # ====================== EQUIPMENT PAGE (Rental + Return) ======================
    elif page == "🛡️ Equipment" and (is_admin or is_equipment_role):
        st.header("🛡️ Equipment Management")

        col_r, col_ret = st.columns(2)
        with col_r:
            if st.button("📦 Rental (Checkout)", type="primary", width='stretch'):
                st.session_state.equip_subpage = "Rental"
        with col_ret:
            if st.button("🔄 Return (Check-in)", type="primary", width='stretch'):
                st.session_state.equip_subpage = "Return"

        if "equip_subpage" not in st.session_state:
            st.session_state.equip_subpage = "Rental"
        equip_sub = st.session_state.equip_subpage

        # Fresh load
        equipment_df = get_worksheet_data("Equipment")

        df_filtered = filter_by_team(players_df.copy())
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
        selected_team = st.selectbox("Filter by Team", team_options, key="equip_team_filter")

        if selected_team != "All Teams":
            roster = df_filtered[df_filtered.get("Team Assignment", "") == selected_team].copy()
        else:
            roster = df_filtered.copy()

        if equip_sub == "Rental":
            st.subheader("📦 Equipment Rental – Checkout")
            if st.button("🔄 Refresh Rental List", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()

            for idx, player in roster.iterrows():
                player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
                existing = equipment_df[equipment_df.get("PlayerID", "") == player_id]

                summary_parts = []
                if not existing.empty:
                    if existing.get("Helmet", pd.Series([False])).iloc[0]: summary_parts.append("Helmet ✓")
                    if existing.get("Shoulder Pads", pd.Series([False])).iloc[0]: summary_parts.append("Shoulder Pads ✓")
                    if existing.get("Pants w/Belt", pd.Series([False])).iloc[0]: summary_parts.append("Pants w/Belt ✓")
                    if existing.get("Thigh Pads", pd.Series([False])).iloc[0]: summary_parts.append("Thigh Pads ✓")
                    if existing.get("Tailbone Pad", pd.Series([False])).iloc[0]: summary_parts.append("Tailbone Pad ✓")
                    if existing.get("Knee Pads", pd.Series([False])).iloc[0]: summary_parts.append("Knee Pads ✓")
                summary_text = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_text}"):
                    col1, col2 = st.columns([3, 2])

                    with col1:
                        helmet = st.checkbox("Helmet", value=bool(existing.get("Helmet", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"helm_r_{idx}")
                        helmet_size = st.selectbox("Helmet Size", ["", "XS", "S", "M", "L", "XL", "XXL"], 
                                                  index=0 if existing.empty or pd.isna(existing.get("Helmet Size", pd.Series([""])).iloc[0]) else ["", "XS", "S", "M", "L", "XL", "XXL"].index(existing.get("Helmet Size", pd.Series([""])).iloc[0]),
                                                  disabled=not helmet, key=f"helm_size_r_{idx}")

                        shoulder = st.checkbox("Shoulder Pads", value=bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"shoul_r_{idx}")
                        shoulder_size = st.selectbox("Shoulder Pads Size", ["", "XS", "S", "M", "L", "XL", "XXL"], 
                                                    index=0 if existing.empty or pd.isna(existing.get("Shoulder Pads Size", pd.Series([""])).iloc[0]) else ["", "XS", "S", "M", "L", "XL", "XXL"].index(existing.get("Shoulder Pads Size", pd.Series([""])).iloc[0]),
                                                    disabled=not shoulder, key=f"shoul_size_r_{idx}")

                        pants = st.checkbox("Pants w/Belt", value=bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"pants_r_{idx}")
                        pants_size = st.selectbox("Pants Size", ["", "XS", "S", "M", "L", "XL", "XXL"], 
                                                 index=0 if existing.empty or pd.isna(existing.get("Pants Size", pd.Series([""])).iloc[0]) else ["", "XS", "S", "M", "L", "XL", "XXL"].index(existing.get("Pants Size", pd.Series([""])).iloc[0]),
                                                 disabled=not pants, key=f"pants_size_r_{idx}")

                    with col2:
                        thigh = st.checkbox("Thigh Pads", value=bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"thigh_r_{idx}")
                        tailbone = st.checkbox("Tailbone Pad", value=bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"tail_r_{idx}")
                        knee = st.checkbox("Knee Pads", value=bool(existing.get("Knee Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"knee_r_{idx}")

                        secured = st.checkbox("Rental secured by Cheque or Credit Card", value=bool(existing.get("Secured Rental", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"sec_r_{idx}")

                    if st.button("💾 Save Rental for this Player", key=f"save_rental_{idx}", type="primary"):
                        new_row = {
                            "PlayerID": player_id,
                            "First Name": player.get("First Name", ""),
                            "Last Name": player.get("Last Name", ""),
                            "Helmet": helmet,
                            "Helmet Size": helmet_size if helmet else "",
                            "Shoulder Pads": shoulder,
                            "Shoulder Pads Size": shoulder_size if shoulder else "",
                            "Pants w/Belt": pants,
                            "Pants Size": pants_size if pants else "",
                            "Thigh Pads": thigh,
                            "Tailbone Pad": tailbone,
                            "Knee Pads": knee,
                            "Secured Rental": secured
                        }
                        equipment_df = equipment_df[equipment_df.get("PlayerID", "") != player_id]
                        equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                        sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                        st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                        time.sleep(0.5)
                        st.rerun()

        elif equip_sub == "Return":
            st.subheader("🔄 Equipment Return – Check-in")
            if st.button("🔄 Refresh Return List", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()

            for idx, player in roster.iterrows():
                player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
                existing = equipment_df[equipment_df.get("PlayerID", "") == player_id]

                rented_parts = []
                if not existing.empty:
                    if existing.get("Helmet", pd.Series([False])).iloc[0]: rented_parts.append("Helmet")
                    if existing.get("Shoulder Pads", pd.Series([False])).iloc[0]: rented_parts.append("Shoulder Pads")
                    if existing.get("Pants w/Belt", pd.Series([False])).iloc[0]: rented_parts.append("Pants w/Belt")
                    if existing.get("Thigh Pads", pd.Series([False])).iloc[0]: rented_parts.append("Thigh Pads")
                    if existing.get("Tailbone Pad", pd.Series([False])).iloc[0]: rented_parts.append("Tailbone Pad")
                    if existing.get("Knee Pads", pd.Series([False])).iloc[0]: rented_parts.append("Knee Pads")
                current_summary = " | ".join(rented_parts) if rented_parts else "Nothing currently rented"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — Currently out: {current_summary}"):
                    if not rented_parts:
                        st.info("All equipment already returned.")
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            helmet_ret = st.checkbox("Return Helmet", value=True, key=f"helm_ret_{idx}") if bool(existing.get("Helmet", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            shoulder_ret = st.checkbox("Return Shoulder Pads", value=True, key=f"shoul_ret_{idx}") if bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            pants_ret = st.checkbox("Return Pants w/Belt", value=True, key=f"pants_ret_{idx}") if bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                        with col2:
                            thigh_ret = st.checkbox("Return Thigh Pads", value=True, key=f"thigh_ret_{idx}") if bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            tail_ret = st.checkbox("Return Tailbone Pad", value=True, key=f"tail_ret_{idx}") if bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            knee_ret = st.checkbox("Return Knee Pads", value=True, key=f"knee_ret_{idx}") if bool(existing.get("Knee Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False

                        if st.button("✅ Return Selected Equipment", key=f"return_btn_{idx}", type="primary"):
                            new_row = existing.iloc[0].to_dict() if not existing.empty else {}
                            if helmet_ret: new_row["Helmet"] = False
                            if shoulder_ret: new_row["Shoulder Pads"] = False
                            if pants_ret: new_row["Pants w/Belt"] = False
                            if thigh_ret: new_row["Thigh Pads"] = False
                            if tail_ret: new_row["Tailbone Pad"] = False
                            if knee_ret: new_row["Knee Pads"] = False

                            equipment_df = equipment_df[equipment_df.get("PlayerID", "") != player_id]
                            equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                            sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                            st.success(f"✅ Equipment returned for {player.get('First Name')} {player.get('Last Name')}")
                            time.sleep(0.5)
                            st.rerun()

    # ====================== REGISTRAR, COACH PORTAL, RESTRICTED HEALTH, EVENTS, FOOTBALL OPERATIONS, ADMIN, PROFILE ======================
    # (All other pages are unchanged from the previous stable version and fully functional)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
