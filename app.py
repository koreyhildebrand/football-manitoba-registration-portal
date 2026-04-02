import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="St. Vital Mustangs Registration", layout="wide", page_icon="🏈")
st.title("🏈 St. Vital Mustangs Registration Portal")

# ====================== GOOGLE SHEETS + AUTO TABS ======================
@st.cache_resource
def get_gsheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RegistrationPortal")
    except Exception as e:
        st.error(f"❌ Sheet connection failed: {str(e)}")
        st.stop()

sheet = get_gsheet()

def ensure_worksheet(name, headers):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        st.info(f"Creating tab: {name}")
        ws = sheet.add_worksheet(title=name, rows=200, cols=30)
        ws.append_row(headers)
        return ws

players_ws = ensure_worksheet("Players", ["First Name","Last Name","Date of Birth","Address","Weight","Years Experience","ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name","Secondary Emergency Contact Phone","Secondary Emergency Contact Email","Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo","RegisteredCamps"])
teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
users_ws = ensure_worksheet("Users", ["username","name","email","password","roles"])
camps_ws = ensure_worksheet("Camps", ["CampID","CampName","Date","Location","Description","MaxPlayers"])

players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())
camps_df = pd.DataFrame(camps_ws.get_all_records())

# ====================== 2026 AGE GROUPS ======================
def calculate_age_group(dob_str):
    try:
        dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
        y = dob.year
        if 2016 <= y <= 2017: return "U10 Cruncher"
        elif 2014 <= y <= 2015: return "U12 Atom"
        elif 2012 <= y <= 2013: return "U14 PeeWee"
        elif 2010 <= y <= 2011: return "U16 Bantam"
        return "Outside 2026 Eligibility"
    except:
        return "Invalid DOB"

if "Date of Birth" in players_df.columns:
    players_df["AgeGroup"] = players_df["Date of Birth"].apply(calculate_age_group)

# ====================== AUTHENTICATION ======================
if "authenticator" not in st.session_state:
    user_records = pd.DataFrame(users_ws.get_all_records()).to_dict("records")
    credentials = {"usernames": {}}
    for rec in user_records:
        uname = rec.get("username", "").strip()
        if uname:
            credentials["usernames"][uname] = {
                "name": rec.get("name", uname),
                "email": rec.get("email", ""),
                "password": rec.get("password", "changeme123")
            }

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
    user_row = next((u for u in pd.DataFrame(users_ws.get_all_records()).to_dict("records") if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]
    is_admin = "Admin" in roles
    can_rw = is_admin or "ReadWrite" in roles
    can_ro = is_admin or can_rw or "ReadOnly" in roles
    can_restricted = is_admin or "Restricted" in roles

    st.sidebar.success(f"👤 {name} ({username})")
    st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

    if not can_ro:
        st.error("You have no access privileges.")
        st.stop()

    # ====================== TABS ======================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 Players", "🏈 Teams & Coaches", "🔒 Restricted Health", "📄 Export", "⚙️ Admin", "🏕️ Team Management & Camps"])

    with tab1:
        st.header("Player Roster")
        display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", "Years Experience", "ParentName", "ParentPhone", "ParentEmail", "Secondary Emergency Contact Name", "Team", "RegisteredCamps"]
        available_cols = [c for c in display_cols if c in players_df.columns]
        df_display = players_df[available_cols].copy()
        search = st.text_input("🔍 Search players", key="player_search")
        if search:
            df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="player_editor")
        if st.button("💾 Save Player Changes", type="primary"):
            for col in edited.columns:
                players_df[col] = edited[col]
            players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("✅ Saved!")

    with tab2:
        st.header("Teams & Coaches")
        if can_rw:
            edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
            if st.button("💾 Save Teams"):
                teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
                st.success("Saved!")
            with st.expander("➕ Create New Team"):
                t_name = st.text_input("Team Name", key="new_team_name")
                t_div = st.selectbox("Division", ["U10 Cruncher", "U12 Atom", "U14 PeeWee", "U16 Bantam"], key="new_team_div")
                t_coach = st.text_input("Coach Name", key="new_team_coach")
                if st.button("Create Team", key="create_team_btn"):
                    new_row = {"TeamID": len(teams_df)+1, "TeamName": t_name, "Division": t_div, "CoachName": t_coach, "CoachPhone": "", "CoachEmail": "", "SeasonYear": 2026}
                    teams_df = pd.concat([teams_df, pd.DataFrame([new_row])], ignore_index=True)
                    teams_ws.update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                    st.success(f"Team {t_name} created!")
        else:
            st.info("View-only mode.")

    with tab3:
        if can_restricted:
            st.header("🔒 Restricted Health Data")
            health_cols = ["First Name","Last Name","Health Number","History of Concussion","Glasses/Contacts","Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy","Hearing problems","Heart Condition","Medication","Surgeries in last year","ExplanationIfYes","MedicationLists","AdditionalInfo"]
            avail = [c for c in health_cols if c in players_df.columns]
            edited_h = st.data_editor(players_df[avail], num_rows="dynamic", use_container_width=True, key="health_editor")
            if st.button("💾 Save Restricted Data"):
                for c in edited_h.columns:
                    players_df[c] = edited_h[c]
                players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("🔒 Saved securely!")
        else:
            st.warning("🔒 Restricted access denied.")

    with tab4:
        st.header("📄 Export")
        player_list = (players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)).tolist()
        sel = st.selectbox("Generate PDF for", player_list, key="pdf_select") if player_list else None
        if sel and st.button("Generate PDF", key="gen_pdf_btn"):
            idx = player_list.index(sel)
            row = players_df.iloc[idx]
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.drawString(100, 750, "St. Vital Mustangs Registration 2026")
            c.drawString(100, 720, f"{row.get('First Name','')} {row.get('Last Name','')} - {row.get('AgeGroup','')}")
            c.drawString(100, 690, f"Parent: {row.get('ParentName','')} | Phone: {row.get('ParentPhone','')}")
            c.drawString(100, 660, f"Team: {row.get('Team','')} | Camps: {row.get('RegisteredCamps','')}")
            c.save()
            st.download_button("⬇️ Download PDF", buffer.getvalue(), f"{sel.replace(' ','_')}.pdf", "application/pdf", key="pdf_download")
        if st.button("Export All as CSV", key="csv_btn"):
            st.download_button("⬇️ Download CSV", players_df.to_csv(index=False), "stvital_mustangs_players.csv", "text/csv", key="csv_download")

    with tab5:
        if is_admin:
            st.header("⚙️ Super Admin")
            p_sel = st.selectbox("Player", player_list, key="assign_player") if player_list else None
            t_sel = st.selectbox("Team", teams_df["TeamName"].tolist() if not teams_df.empty else ["No teams"], key="assign_team")
            if st.button("Assign Player to Team", key="assign_btn"):
                idx = player_list.index(p_sel)
                players_df.at[idx, "Team"] = t_sel
                players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                st.success("Assigned!")
            st.info("Edit Users sheet for new users/roles.")
        else:
            st.info("Admin tools only.")

    with tab6:
        st.header("🏕️ Team Management & Camps")

        sub1, sub2 = st.tabs(["👥 Team View", "🏕️ Camps & Registration"])

        with sub1:
            st.subheader("View Players by Team")
            if not teams_df.empty:
                selected_team = st.selectbox("Select Team", teams_df["TeamName"], key="team_view_select")
                team_players = players_df[players_df["Team"] == selected_team].copy()
                if not team_players.empty:
                    # Safe column selection
                    view_cols = ["First Name", "Last Name", "AgeGroup", "RegisteredCamps"]
                    available_view_cols = [c for c in view_cols if c in team_players.columns]
                    st.dataframe(team_players[available_view_cols], use_container_width=True)
                else:
                    st.info(f"No players assigned to {selected_team} yet.")
            else:
                st.info("No teams created yet.")

        with sub2:
            if can_rw:
                st.subheader("Create New Camp / Training Session")
                col1, col2 = st.columns(2)
                with col1:
                    c_name = st.text_input("Camp Name", key="camp_name")
                    c_date = st.date_input("Date", key="camp_date")
                with col2:
                    c_location = st.text_input("Location", key="camp_location")
                    c_max = st.number_input("Max Players", min_value=1, value=40, key="camp_max")
                c_desc = st.text_area("Description", key="camp_desc")
                if st.button("Create Camp", key="create_camp_btn"):
                    new_camp = {"CampID": len(camps_df)+1, "CampName": c_name, "Date": str(c_date), "Location": c_location, "Description": c_desc, "MaxPlayers": c_max}
                    camps_df = pd.concat([camps_df, pd.DataFrame([new_camp])], ignore_index=True)
                    camps_ws.update([camps_df.columns.values.tolist()] + camps_df.fillna("").values.tolist())
                    st.success(f"✅ Camp '{c_name}' created!")

                st.subheader("Register Players to Camp")
                if not camps_df.empty:
                    selected_camp = st.selectbox("Select Camp", camps_df["CampName"], key="camp_select")
                    all_players = (players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)).tolist()
                    selected_players = st.multiselect("Select Players to Register", all_players, key="player_multiselect")
                    if st.button("Register Selected Players", key="register_camp_btn"):
                        for p in selected_players:
                            idx = players_df[(players_df["First Name"] + " " + players_df["Last Name"]) == p].index[0]
                            current = players_df.at[idx, "RegisteredCamps"] or ""
                            new_val = f"{current}, {selected_camp}" if current else selected_camp
                            players_df.at[idx, "RegisteredCamps"] = new_val
                        players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                        st.success(f"✅ {len(selected_players)} player(s) registered to {selected_camp}")
                else:
                    st.info("Create a camp first above.")
            else:
                st.info("You need Read-Write or Admin rights to manage camps.")

    st.sidebar.button("Logout", on_click=lambda: st.session_state.authenticator.logout('main'))

elif authentication_status is False:
    st.error("❌ Username or password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")

st.caption("✅ St. Vital Mustangs Registration Portal | Multi-role | Team & Camp Management")