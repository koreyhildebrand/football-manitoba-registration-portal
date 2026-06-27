import streamlit as st
import pandas as pd
import datetime
import time
from utils.sheets import get_live_equipment
from utils.helpers import to_bool

def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment page – Fixed column name compatibility"""
    st.header("🛡️ Equipment Management")

    # ====================== COLUMN NAME NORMALIZATION ======================
    # Make the code work with both old ("First Name") and new ("first_name") column styles
    col_map = {
        "first_name": "First Name",
        "last_name": "Last Name",
        "birthdate": "Birthdate",
        "timestamp": "Timestamp",
        "team assignment": "Team Assignment",
        "weight": "Weight"
    }

    df = players_df.copy()
    for old, new in col_map.items():
        if old in df.columns:
            df[new] = df[old]
        elif new in df.columns:
            df[old] = df[new]  # ensure both exist

    # ====================== SUB-PAGE BUTTONS ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📦 Rental (Checkout)", type="primary"):
            st.session_state.equip_subpage = "Rental"
    with col2:
        if st.button("📋 All Current Rentals", type="primary"):
            st.session_state.equip_subpage = "All Rentals"
    with col3:
        if st.button("➕ Private Rental", type="primary"):
            st.session_state.equip_subpage = "Private Rental"

    if "equip_subpage" not in st.session_state:
        st.session_state.equip_subpage = "Rental"
    equip_sub = st.session_state.equip_subpage

    # ====================== PRIVATE RENTAL CREATION ======================
    if equip_sub == "Private Rental":
        st.subheader("➕ Create Private Rental Player")
        st.caption("These players are for equipment rental only and are **not** added to the main Players sheet.")
        with st.form("private_rental_form"):
            first_name = st.text_input("First Name *", key="pr_first")
            last_name = st.text_input("Last Name *", key="pr_last")
            birthdate = st.date_input("Birthdate (optional)", value=None, key="pr_birthdate")
            phone = st.text_input("Phone Number (optional)", key="pr_phone")
            submitted = st.form_submit_button("Create Private Rental Player")
            if submitted:
                if not first_name or not last_name:
                    st.error("First Name and Last Name are required.")
                else:
                    player_id = f"Private_{first_name.strip()}_{last_name.strip()}_{str(birthdate) if birthdate else 'N/A'}"
                    new_row = {
                        "PlayerID": player_id,
                        "First Name": first_name.strip(),
                        "Last Name": last_name.strip(),
                        "Birthdate": str(birthdate) if birthdate else "",
                        "Phone": phone.strip() if phone else "",
                        "Team Assignment": "Private Rental",
                        "Helmet": False, "Shoulder Pads": False, "Pants": False,
                        "Thigh Pads": False, "Hip Pads": False, "Tailbone Pad": False,
                        "Knee Pads": False, "Mouth Guard": False, "Belt": False,
                        "Practice Jersey Red": False, "Practice Jersey Black": False,
                        "Practice Jersey White": False,
                        "RentalDate": "", "ReturnDate": ""
                    }
                    equipment_df = get_live_equipment()
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Private rental player '{first_name} {last_name}' created!")
                    time.sleep(1)
                    st.rerun()
        return

    # ====================== REGULAR RENTAL / ALL RENTALS ======================
    selected_year = st.selectbox("Select Rental Year", [2024, 2025, 2026, 2027], index=2, key="equip_year")

    # Safe PlayerID creation with fallbacks
    df = df.copy()
    df['PlayerID'] = (
        df.get('First Name', df.get('first_name', pd.Series(['']*len(df)))).astype(str).str.strip() + "_" +
        df.get('Last Name', df.get('last_name', pd.Series(['']*len(df)))).astype(str).str.strip() + "_" +
        df.get('Birthdate', df.get('birthdate', pd.Series(['']*len(df)))).astype(str).str.strip()
    )

    if 'Timestamp' in df.columns or 'timestamp' in df.columns:
        ts_col = 'Timestamp' if 'Timestamp' in df.columns else 'timestamp'
        df['RegYear'] = pd.to_datetime(df[ts_col], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values(ts_col, ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # Load Private Rental players
    equipment_df = get_live_equipment()
    private_rentals = equipment_df[equipment_df.get("Team Assignment", "") == "Private Rental"].copy()

    team_list = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) + ["Private Rental"]
    selected_team = st.selectbox("Select Team", team_list, key="equip_team_filter")

    if selected_team == "All Players":
        roster = df.copy()
    elif selected_team == "Private Rental":
        roster = private_rentals.copy()
    else:
        roster = df[df.get("Team Assignment", df.get("team assignment", pd.Series([""]*len(df)))) == selected_team].copy()

    # ... (the rest of your original code for "Rental" and "All Rentals" stays exactly the same)

    if equip_sub == "Rental":
        # [Your entire original Rental block remains unchanged – just paste it here]
        st.subheader(f"📦 Rental / Return – {selected_team} ({selected_year} Season)")
        # ... (keep everything from "if st.button("🔄 Refresh List"..." down to the end of the Rental section)

    elif equip_sub == "All Rentals":
        # [Your entire original All Rentals block remains unchanged]
        st.subheader(f"📋 All Current Rentals")
        # ... (keep the rest of your All Rentals code)

    st.caption(f"✅ St. Vital Mustangs Registration Portal | v4.05")
