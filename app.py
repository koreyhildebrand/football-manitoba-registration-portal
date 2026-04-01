import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import streamlit_authenticator as stauth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="Football Manitoba Registration Portal", layout="wide", page_icon="🏈")
st.title("🏈 Football Manitoba Admin Registration Portal")

# ====================== GOOGLE SHEETS CONNECTION + AUTO-CREATE TABS ======================
@st.cache_resource
def get_gsheet():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("RegistrationPortal")
    except Exception as e:
        st.error(f"❌ Google Sheet connection failed. Check secrets and sheet name 'RegistrationPortal'. Error: {str(e)}")
        st.stop()

sheet = get_gsheet()

def ensure_worksheet(name, headers):
    try:
        return sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        st.info(f"Creating missing tab: {name}")
        ws = sheet.add_worksheet(title=name, rows=200, cols=30)
        ws.append_row(headers)
        return ws

players_ws = ensure_worksheet("Players", [
    "First Name","Last Name","Date of Birth","Address","Weight","Years Experience",
    "ParentName","ParentPhone","ParentEmail","Secondary Emergency Contact Name",
    "Secondary Emergency Contact Phone","Secondary Emergency Contact Email",
    "Team","AgeGroup","Health Number","History of Concussion","Glasses/Contacts",
    "Asthma","Diabetic","Allergies","Injuries in past year","Epilepsy",
    "Hearing problems","Heart Condition","Medication","Surgeries in last year",
    "ExplanationIfYes","MedicationLists","AdditionalInfo"
])

teams_ws = ensure_worksheet("Teams", ["TeamID","TeamName","Division","CoachName","CoachPhone","CoachEmail","SeasonYear"])
users_ws = ensure_worksheet("Users", ["username","name","email","password","roles"])

# Load data
players_df = pd.DataFrame(players_ws.get_all_records())
teams_df = pd.DataFrame(teams_ws.get_all_records())

# ====================== AGE GROUP (Football Manitoba 2026) ======================
def calculate_age_group(dob_str):
    try:
        dob = datetime.datetime.strptime(str(dob_str).strip(), "%Y-%m-%d").date()
        birth_year = dob.year
        if 2016 <= birth_year <= 2017:
            return "U10 Cruncher"
        elif 2014 <= birth_year <= 2015:
            return "U12 Atom"
        elif 2012 <= birth_year <= 2013:
            return "U14 PeeWee"
        elif 2010 <= birth_year <= 2011:
            return "U16 Bantam"
        else:
            return "Outside 2026 MMFA Eligibility"
    except:
        return "Invalid DOB"

if "Date of Birth" in players_df.columns:
    players_df["AgeGroup"] = players_df["Date of Birth"].apply(calculate_age_group)

# ====================== SAFE USERS LOADING ======================
user_values = users_ws.get_all_values()
if len(user_values) <= 1 or not any(user_values[0]):
    users_ws.append_row(["username","name","email","password","roles"])

headers = [str(h).strip() for h in user_values[0]] if user_values else []
user_records = []
for row in user_values[1:]:
    record = {headers[i]: str(row[i]).strip() if i < len(row) else "" for i in range(len(headers))}
    if record.get("username"):
        user_records.append(record)

credentials = {"usernames": {}}
for rec in user_records:
    uname = rec.get("username", "").strip()
    if uname:
        credentials["usernames"][uname] = {
            "name": rec.get("name", uname),
            "email": rec.get("email", ""),
            "password": rec.get("password", "changeme123")
        }

if not credentials["usernames"]:
    st.error("❌ No users found in Users sheet. Add at least one Admin user (username: admin, roles: Admin).")
    st.stop()

# ====================== AUTHENTICATION (Fixed for latest streamlit-authenticator) ======================
if "authenticator" not in st.session_state:
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="football_mb_portal",
        key="super_secret_key_2026_mb",
        cookie_expiry_days=30,
    )
    st.session_state.authenticator = authenticator
    st.session_state.user_roles = {}

# Use fields to force a clear "Login" button and avoid form submit error
name, authentication_status, username = st.session_state.authenticator.login(
    location='main',
    fields={
        'Form name': 'Login',
        'Username': 'Username',
        'Password': 'Password',
        'Login': 'Login'   # This ensures the submit button appears correctly
    }
)

if authentication_status is False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status is None:
    st.warning("Please enter your username and password")
    st.stop()

# Load roles safely
if username and username not in st.session_state.user_roles:
    user_row = next((u for u in user_records if u.get("username") == username), None)
    roles_str = user_row.get("roles", "") if user_row else ""
    st.session_state.user_roles[username] = [r.strip() for r in roles_str.split(",") if r.strip()]

roles = st.session_state.user_roles.get(username, [])
is_admin = "Admin" in roles
can_rw = is_admin or "ReadWrite" in roles
can_ro = is_admin or can_rw or "ReadOnly" in roles
can_restricted = is_admin or "Restricted" in roles

st.sidebar.success(f"👤 {name} ({username})")
st.sidebar.write("**Roles:**", ", ".join(roles) if roles else "None")

if not can_ro:
    st.error("You have no access privileges.")
    st.stop()

# ====================== MAIN TABS ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Players", "🏈 Teams & Coaches", "🔒 Restricted Health", "📄 Export", "⚙️ Admin"])

with tab1:
    st.header("Player Roster")
    display_cols = ["First Name", "Last Name", "Date of Birth", "AgeGroup", "Address", "Weight", 
                    "Years Experience", "ParentName", "ParentPhone", "ParentEmail", 
                    "Secondary Emergency Contact Name", "Team"]
    available_cols = [c for c in display_cols if c in players_df.columns]
    df_display = players_df[available_cols].copy()
    
    search = st.text_input("🔍 Search players", "")
    if search:
        df_display = df_display[df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="player_editor")
    
    if st.button("💾 Save Player Changes to Google Sheet", type="primary"):
        for col in edited.columns:
            players_df[col] = edited[col]
        players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
        st.success("✅ Player data saved!")

with tab2:
    st.header("Teams & Coach Assignment")
    if can_rw:
        edited_teams = st.data_editor(teams_df, num_rows="dynamic", use_container_width=True, key="team_editor")
        if st.button("💾 Save Teams"):
            teams_ws.update([edited_teams.columns.values.tolist()] + edited_teams.fillna("").values.tolist())
            st.success("Teams saved!")
        
        with st.expander("➕ Create New Team"):
            t_name = st.text_input("Team Name")
            t_div = st.selectbox("Division", ["U10 Cruncher", "U12 Atom", "U14 PeeWee", "U16 Bantam"])
            t_coach = st.text_input("Coach Name")
            t_phone = st.text_input("Coach Phone")
            t_email = st.text_input("Coach Email")
            if st.button("Create Team"):
                new_row = {"TeamID": len(teams_df)+1, "TeamName": t_name, "Division": t_div,
                           "CoachName": t_coach, "CoachPhone": t_phone, "CoachEmail": t_email, "SeasonYear": 2026}
                teams_df = pd.concat([teams_df, pd.DataFrame([new_row])], ignore_index=True)
                teams_ws.update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                st.success(f"✅ Team {t_name} created!")
    else:
        st.info("View-only. Contact Admin for editing rights.")

with tab3:
    if can_restricted:
        st.header("🔒 Restricted Health Information")
        health_cols = ["First Name", "Last Name", "Health Number", "History of Concussion", "Glasses/Contacts",
                       "Asthma", "Diabetic", "Allergies", "Injuries in past year", "Epilepsy",
                       "Hearing problems", "Heart Condition", "Medication", "Surgeries in last year",
                       "ExplanationIfYes", "MedicationLists", "AdditionalInfo"]
        available_health = [c for c in health_cols if c in players_df.columns]
        restricted_df = players_df[available_health]
        
        edited_health = st.data_editor(restricted_df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Restricted Data"):
            for col in edited_health.columns:
                players_df[col] = edited_health[col]
            players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("🔒 Health data saved securely.")
    else:
        st.warning("🔒 You do not have permission to view restricted health data.")

with tab4:
    st.header("📄 PDF Registration Forms & Export")
    player_options = (players_df["First Name"].astype(str) + " " + players_df["Last Name"].astype(str)).tolist()
    selected = st.selectbox("Select player for PDF", player_options) if player_options else None
    
    if selected and st.button("Generate PDF"):
        idx = player_options.index(selected)
        row = players_df.iloc[idx]
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Football Manitoba Registration Portal - 2026")
        c.drawString(100, 720, f"Player: {row.get('First Name','')} {row.get('Last Name','')}")
        c.drawString(100, 690, f"DOB: {row.get('Date of Birth','')} | Age Group: {row.get('AgeGroup','')}")
        c.drawString(100, 660, f"Parent: {row.get('ParentName','')} | {row.get('ParentPhone','')}")
        c.drawString(100, 630, f"Team: {row.get('Team','')}")
        c.save()
        st.download_button("⬇️ Download PDF", buffer.getvalue(), f"{selected.replace(' ', '_')}_2026.pdf", "application/pdf")

    if st.button("Export All Players as CSV"):
        csv = players_df.to_csv(index=False)
        st.download_button("⬇️ Download Full CSV", csv, "football_mb_players_2026.csv", "text/csv")

with tab5:
    if is_admin:
        st.header("⚙️ Super Admin Tools")
        st.subheader("Assign Player to Team")
        p_select = st.selectbox("Select Player", player_options) if player_options else "No players"
        t_select = st.selectbox("Assign to Team", teams_df["TeamName"].tolist() if not teams_df.empty else ["No teams"])
        if st.button("Assign Player"):
            idx = player_options.index(p_select)
            players_df.at[idx, "Team"] = t_select
            players_ws.update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
            st.success("Player assigned!")
        
        st.info("Manage users by editing the **Users** sheet directly in Google Sheets (roles comma-separated).")
    else:
        st.info("Super Admin tools are only for Admin role.")

st.sidebar.button("Logout", on_click=lambda: st.session_state.authenticator.logout(location='main'))

st.caption("✅ Fixed login form + submit button | Multi-role support | Football Manitoba 2026 Age Groups | Auto tab creation")