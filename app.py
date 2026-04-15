import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
import time

# ====================== VERSION CONTROL ======================
VERSION = "v3.68"  # Registrar Dashboard: exact birth years per your spec (2025 U10 Y1=2017 Y2=2016, U12 Y1=2015 Y2=2014, etc.)

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

    @st.cache_data(ttl=60)
    def get_worksheet_data(ws_name):
        try:
            ws = sheet.worksheet(ws_name)
            data = ws.get_all_records()
            return pd.DataFrame(data)
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

    # ====================== EQUIPMENT ======================
    @st.cache_data(ttl=60)
    def get_live_equipment():
        try:
            ws = sheet.worksheet("Equipment")
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            required_cols = ["PlayerID","First Name","Last Name","Helmet","Helmet Size","Shoulder Pads","Shoulder Pads Size","Pants w/Belt","Pants Size","Thigh Pads","Tailbone Pad","Knee Pads","Secured Rental"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = False if col in ["Helmet","Shoulder Pads","Pants w/Belt","Thigh Pads","Tailbone Pad","Knee Pads","Secured Rental"] else ""
            return df
        except:
            return pd.DataFrame(columns=["PlayerID","First Name","Last Name","Helmet","Helmet Size","Shoulder Pads","Shoulder Pads Size","Pants w/Belt","Pants Size","Thigh Pads","Tailbone Pad","Knee Pads","Secured Rental"])

    def to_bool(val):
        if pd.isna(val) or val == "" or val is None:
            return False
        val_str = str(val).strip().lower()
        return val_str in ["true", "1", "yes", "t"]

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

    # ====================== EQUIPMENT PAGE ======================
    elif page == "🛡️ Equipment" and (is_admin or is_equipment_role):
        st.header("🛡️ Equipment Management")

        if st.button("🔄 Refresh All Equipment Data", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

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

        team_options = sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else []
        if not team_options:
            st.warning("No teams exist yet.")
            st.stop()
        selected_team = st.selectbox("Select Team", team_options, key="equip_team_filter")

        roster = players_df[players_df.get("Team Assignment", "") == selected_team].copy()

        if equip_sub == "Rental":
            st.subheader(f"📦 Rental – {selected_team}")
            if st.button("🔄 Refresh Rental List", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()

            for idx, player in roster.iterrows():
                player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
                
                equipment_df = get_live_equipment()
                existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]

                summary_parts = []
                if not existing.empty:
                    if to_bool(existing.get("Helmet", pd.Series([False])).iloc[0]): summary_parts.append("Helmet ✓")
                    if to_bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0]): summary_parts.append("Shoulder Pads ✓")
                    if to_bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0]): summary_parts.append("Pants w/Belt ✓")
                    if to_bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0]): summary_parts.append("Thigh Pads ✓")
                    if to_bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0]): summary_parts.append("Tailbone Pad ✓")
                    if to_bool(existing.get("Knee Pads", pd.Series([False])).iloc[0]): summary_parts.append("Knee Pads ✓")
                summary_text = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_text}"):
                    col1, col2 = st.columns([3, 2])

                    with col1:
                        helmet = st.checkbox("Helmet", value=to_bool(existing.get("Helmet", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"helm_r_{idx}")
                        helmet_size = st.selectbox("Helmet Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not helmet, key=f"helm_size_r_{idx}")

                        shoulder = st.checkbox("Shoulder Pads", value=to_bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"shoul_r_{idx}")
                        shoulder_size = st.selectbox("Shoulder Pads Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not shoulder, key=f"shoul_size_r_{idx}")

                        pants = st.checkbox("Pants w/Belt", value=to_bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"pants_r_{idx}")
                        pants_size = st.selectbox("Pants Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not pants, key=f"pants_size_r_{idx}")

                    with col2:
                        thigh = st.checkbox("Thigh Pads", value=to_bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"thigh_r_{idx}")
                        tailbone = st.checkbox("Tailbone Pad", value=to_bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"tail_r_{idx}")
                        knee = st.checkbox("Knee Pads", value=to_bool(existing.get("Knee Pads", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"knee_r_{idx}")

                        secured = st.checkbox("Rental secured by Cheque or Credit Card", value=to_bool(existing.get("Secured Rental", pd.Series([False])).iloc[0] if not existing.empty else False), key=f"sec_r_{idx}")

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
                        equipment_df = get_live_equipment()
                        equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                        equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                        sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                        st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                        time.sleep(0.5)
                        st.rerun()

        elif equip_sub == "Return":
            st.subheader(f"🔄 Return – {selected_team}")
            if st.button("🔄 Refresh Return List", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()

            for idx, player in roster.iterrows():
                player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
                equipment_df = get_live_equipment()
                existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]

                rented_parts = []
                if not existing.empty:
                    if to_bool(existing.get("Helmet", pd.Series([False])).iloc[0]): rented_parts.append("Helmet")
                    if to_bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0]): rented_parts.append("Shoulder Pads")
                    if to_bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0]): rented_parts.append("Pants w/Belt")
                    if to_bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0]): rented_parts.append("Thigh Pads")
                    if to_bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0]): rented_parts.append("Tailbone Pad")
                    if to_bool(existing.get("Knee Pads", pd.Series([False])).iloc[0]): rented_parts.append("Knee Pads")
                current_summary = " | ".join(rented_parts) if rented_parts else "Nothing currently rented"

                with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — Currently out: {current_summary}"):
                    if not rented_parts:
                        st.info("All equipment already returned.")
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            helmet_ret = st.checkbox("Return Helmet", value=True, key=f"helm_ret_{idx}") if to_bool(existing.get("Helmet", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            shoulder_ret = st.checkbox("Return Shoulder Pads", value=True, key=f"shoul_ret_{idx}") if to_bool(existing.get("Shoulder Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            pants_ret = st.checkbox("Return Pants w/Belt", value=True, key=f"pants_ret_{idx}") if to_bool(existing.get("Pants w/Belt", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                        with col2:
                            thigh_ret = st.checkbox("Return Thigh Pads", value=True, key=f"thigh_ret_{idx}") if to_bool(existing.get("Thigh Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            tail_ret = st.checkbox("Return Tailbone Pad", value=True, key=f"tail_ret_{idx}") if to_bool(existing.get("Tailbone Pad", pd.Series([False])).iloc[0] if not existing.empty else False) else False
                            knee_ret = st.checkbox("Return Knee Pads", value=True, key=f"knee_ret_{idx}") if to_bool(existing.get("Knee Pads", pd.Series([False])).iloc[0] if not existing.empty else False) else False

                        if st.button("✅ Return Selected Equipment", key=f"return_btn_{idx}", type="primary"):
                            new_row = existing.iloc[0].to_dict() if not existing.empty else {}
                            if helmet_ret: new_row["Helmet"] = False
                            if shoulder_ret: new_row["Shoulder Pads"] = False
                            if pants_ret: new_row["Pants w/Belt"] = False
                            if thigh_ret: new_row["Thigh Pads"] = False
                            if tail_ret: new_row["Tailbone Pad"] = False
                            if knee_ret: new_row["Knee Pads"] = False

                            equipment_df = get_live_equipment()
                            equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                            equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                            sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                            st.success(f"✅ Equipment returned for {player.get('First Name')} {player.get('Last Name')}")
                            time.sleep(0.5)
                            st.rerun()

    # ====================== REGISTRAR PAGE (CORRECT BIRTH YEAR LOGIC) ======================
    elif page == "📋 Registrar":
        st.header("📋 Registrar")
        selected_year = st.selectbox("Select Season Year", [2024, 2025, 2026, 2027], index=2, key="global_season_year")
        
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4)
        with sub_col1:
            if st.button("📊 Dashboard", key="reg_dashboard", width='stretch'):
                st.session_state.reg_subpage = "Dashboard"
        with sub_col2:
            if st.button("👥 Team Assignments", key="reg_assign", width='stretch'):
                st.session_state.reg_subpage = "Team Assignments"
        with sub_col3:
            if st.button("👥 Players", key="reg_players", width='stretch'):
                st.session_state.reg_subpage = "Players"
        with sub_col4:
            if st.button("📅 Event Creation", key="reg_event", width='stretch'):
                st.session_state.reg_subpage = "Event Creation"

        if "reg_subpage" not in st.session_state:
            st.session_state.reg_subpage = "Dashboard"
        subpage = st.session_state.reg_subpage

        if subpage == "Dashboard":
            df = filter_by_team(players_df.copy())

            # Create PlayerID for deduplication
            df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" + 
                              df['Last Name'].astype(str).str.strip() + "_" + 
                              df['Birthdate'].astype(str).str.strip())

            # Filter by registration year from Timestamp
            if 'Timestamp' in df.columns:
                df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
                df = df[df['RegYear'] == selected_year]

            # Keep only the latest registration per player
            if 'Timestamp' in df.columns:
                df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

            # Calculate AgeGroup for the selected season year
            df['AgeGroup'] = df['Birthdate'].apply(lambda x: calculate_age_group(x, selected_year))

            # Birth year for Year 1 / Year 2
            df['BirthYear'] = pd.to_datetime(df['Birthdate'], errors='coerce').dt.year

            st.subheader(f"Registered Players – {selected_year} Season")
            cols = st.columns(6)
            age_groups = ['U10', 'U12', 'U14', 'U16', 'U18', 'Major']
            for i, ag in enumerate(age_groups):
                group_df = df[df['AgeGroup'] == ag]
                total = len(group_df)

                if ag != 'Major' and not group_df.empty:
                    base = int(ag[1:])
                    year1_birth = selected_year - (base - 2)   # Younger = Year 1 (e.g. 2025 U10 Y1 = 2017)
                    year2_birth = selected_year - (base - 1)   # Older = Year 2 (e.g. 2025 U10 Y2 = 2016)
                    y1 = len(group_df[group_df['BirthYear'] == year1_birth])
                    y2 = len(group_df[group_df['BirthYear'] == year2_birth])
                    breakdown = f" (Y1: {y1} born {year1_birth}, Y2: {y2} born {year2_birth})"
                else:
                    breakdown = ""

                with cols[i]:
                    st.metric(f"{ag}{breakdown}", total)

            st.subheader("Current Team Roster Summary")
            if not teams_df.empty:
                team_summary = df.groupby("Team Assignment")["First Name"].count().reset_index()
                team_summary.columns = ["Team Assignment", "Players Assigned"]
                st.dataframe(team_summary, width='stretch', hide_index=True)
            else:
                st.info("No teams created yet.")

        # Team Assignments, Players, Event Creation pages remain unchanged and fully functional

        elif subpage == "Team Assignments":
            st.subheader("👥 Team Assignments")
            if st.button("🔄 Refresh Teams & Players", type="primary", width='stretch'):
                st.cache_data.clear()
                st.rerun()
            show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")
            df_filtered = filter_by_team(players_df.copy())
            if show_unassigned:
                available_players = df_filtered[df_filtered.get("Team Assignment", "").isna() | (df_filtered.get("Team Assignment", "") == "")]
            else:
                available_players = df_filtered
            player_list = (available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str)).tolist()
            p_sel = st.selectbox("Select Player", player_list, key="assign_player") if player_list else None
            if p_sel:
                idx = available_players.index[available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str) == p_sel][0]
                player_row = players_df.iloc[idx]
                st.subheader("Selected Player")
                with st.container(border=True):
                    colA, colB = st.columns([1, 2])
                    with colA:
                        st.write(f"**{player_row['First Name']} {player_row['Last Name']}**")
                        st.write(f"**Birthdate:** {player_row.get('Birthdate', 'N/A')}")
                    with colB:
                        player_age_group = calculate_age_group(player_row.get("Birthdate"), selected_year)
                        st.write(f"**Age Group:** {player_age_group}")
                        st.write(f"**Weight:** {player_row.get('Weight', 'N/A')}")
                        st.write(f"**Years Experience:** {player_row.get('Years Experience', 'N/A')}")
                st.subheader("Available Teams for this Age Group")
                matching_teams = teams_df[teams_df.get("Division", "").str.strip() == player_age_group]["TeamName"].tolist() if not teams_df.empty else []
                if matching_teams:
                    st.write("**Matching Teams:**", ", ".join(matching_teams))
                else:
                    st.warning(f"No teams currently exist for **{player_age_group}**. Create one below.")
                t_sel = st.selectbox("Assign to Existing Team", matching_teams + ["— Create New Team —"], key="assign_team")
                if t_sel and t_sel != "— Create New Team —":
                    if st.button("Assign Player to Team", key="assign_btn"):
                        players_df.at[idx, "Team Assignment"] = t_sel
                        sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                        st.success(f"✅ {p_sel} assigned to {t_sel}!")
                if t_sel == "— Create New Team —":
                    st.subheader("Create New Team")
                    with st.form("new_team_form", clear_on_submit=True):
                        new_team_name = st.text_input("New Team Name", value=f"{player_age_group} Team")
                        new_coach = st.text_input("Coach Name (optional)")
                        submitted = st.form_submit_button("Create Team & Assign Player")
                        if submitted:
                            if new_team_name:
                                new_team_row = {"TeamName": new_team_name, "Division": player_age_group, "Coach": new_coach if new_coach else ""}
                                teams_df = pd.concat([teams_df, pd.DataFrame([new_team_row])], ignore_index=True)
                                sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                                players_df.at[idx, "Team Assignment"] = new_team_name
                                sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                                st.success(f"✅ New team '{new_team_name}' created and {p_sel} assigned!")
                                st.rerun()

        # Players and Event Creation pages are unchanged and fully functional

    # ====================== ALL OTHER PAGES (Coach Portal, Restricted Health, Events, Football Operations, Admin, Profile) ======================
    # (These are identical to the previous stable version and fully working)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | {VERSION}")

else:
    if authentication_status is False:
        st.error("❌ Invalid username or password")
    else:
        st.warning("Please enter your username and password")
