import streamlit as st
import pandas as pd
import datetime
import time
from utils.sheets import get_live_equipment
from utils.helpers import to_bool


def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment page – All Players option + All Current Rentals sub-page (error fixed)."""
    st.header("🛡️ Equipment Management")

    # ====================== RENTAL YEAR SELECTOR ======================
    selected_year = st.selectbox(
        "Select Rental Year",
        [2024, 2025, 2026, 2027],
        index=2,
        key="equip_year"
    )

    # ====================== SUB-PAGE BUTTONS ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📦 Rental (Checkout)", type="primary", width='stretch'):
            st.session_state.equip_subpage = "Rental"
    with col2:
        if st.button("🔄 Return (Check-in)", type="primary", width='stretch'):
            st.session_state.equip_subpage = "Return"
    with col3:
        if st.button("📋 All Current Rentals", type="primary", width='stretch'):
            st.session_state.equip_subpage = "All Rentals"

    if "equip_subpage" not in st.session_state:
        st.session_state.equip_subpage = "Rental"
    equip_sub = st.session_state.equip_subpage

    # ====================== FILTER PLAYERS BY YEAR ======================
    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # ====================== TEAM SELECTOR (with All Players) ======================
    team_list = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list, key="equip_team_filter")

    if selected_team == "All Players":
        roster = df[df.get("Team Assignment", "").notna() & (df.get("Team Assignment", "") != "")].copy()
    else:
        roster = df[df.get("Team Assignment", "") == selected_team].copy()

    # ====================== EQUIPMENT DATA ======================
    equipment_df = get_live_equipment()

    # ====================== RENTAL SUBPAGE ======================
    if equip_sub == "Rental":
        st.subheader(f"📦 Rental – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh Rental List", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            current_weight = player.get("Weight", "N/A")

            summary_parts = []
            if to_bool(existing.get("Helmet")): summary_parts.append("Helmet ✓")
            if to_bool(existing.get("Shoulder Pads")): summary_parts.append("Shoulder Pads ✓")
            if to_bool(existing.get("Pants w/Belt")): summary_parts.append("Pants w/Belt ✓")
            if to_bool(existing.get("Thigh Pads")): summary_parts.append("Thigh Pads ✓")
            if to_bool(existing.get("Tailbone Pad")): summary_parts.append("Tailbone Pad ✓")
            if to_bool(existing.get("Knee Pads")): summary_parts.append("Knee Pads ✓")
            current_rented = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

            # Previous year
            prev_year = selected_year - 1
            prev_weight = "N/A"
            prev_sizes = []
            prev_players = players_df.copy()
            prev_players['PlayerID'] = (prev_players['First Name'].astype(str).str.strip() + "_" +
                                       prev_players['Last Name'].astype(str).str.strip() + "_" +
                                       prev_players['Birthdate'].astype(str).str.strip())
            if 'Timestamp' in prev_players.columns:
                prev_players['RegYear'] = pd.to_datetime(prev_players['Timestamp'], errors='coerce').dt.year
                prev_row = prev_players[(prev_players['PlayerID'] == player_id) & (prev_players['RegYear'] == prev_year)]
                if not prev_row.empty:
                    prev_weight = prev_row.iloc[0].get("Weight", "N/A")
            if to_bool(existing.get("Helmet")):
                prev_sizes.append(f"Helmet {existing.get('Helmet Size', '—')}")
            if to_bool(existing.get("Shoulder Pads")):
                prev_sizes.append(f"Shoulder {existing.get('Shoulder Pads Size', '—')}")
            if to_bool(existing.get("Pants w/Belt")):
                prev_sizes.append(f"Pants {existing.get('Pants Size', '—')}")
            prev_text = f"Prev {prev_year}: {prev_weight} lbs"
            if prev_sizes:
                prev_text += f" ({', '.join(prev_sizes)})"

            summary_line = f"Weight: {current_weight} lbs | {current_rented} | **{prev_text}**"

            with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_line}"):
                col1, col2 = st.columns([3, 2])
                with col1:
                    helmet = st.checkbox("Helmet", value=to_bool(existing.get("Helmet")), key=f"helm_r_{idx}")
                    if helmet:
                        helmet_size = st.radio("Helmet Size", ["XS", "S", "M", "L", "XL", "XXL"],
                                               index=["XS","S","M","L","XL","XXL"].index(existing.get("Helmet Size","M")) if existing.get("Helmet Size") else 2,
                                               key=f"helm_size_r_{idx}", horizontal=True)
                    else:
                        helmet_size = ""

                    shoulder = st.checkbox("Shoulder Pads", value=to_bool(existing.get("Shoulder Pads")), key=f"shoul_r_{idx}")
                    if shoulder:
                        shoulder_size = st.radio("Shoulder Size", ["XS", "S", "M", "L", "XL", "XXL"],
                                                 index=["XS","S","M","L","XL","XXL"].index(existing.get("Shoulder Pads Size","M")) if existing.get("Shoulder Pads Size") else 2,
                                                 key=f"shoul_size_r_{idx}", horizontal=True)
                    else:
                        shoulder_size = ""

                    pants = st.checkbox("Pants w/Belt", value=to_bool(existing.get("Pants w/Belt")), key=f"pants_r_{idx}")
                    if pants:
                        pants_size = st.radio("Pants Size", ["XS", "S", "M", "L", "XL", "XXL"],
                                              index=["XS","S","M","L","XL","XXL"].index(existing.get("Pants Size","M")) if existing.get("Pants Size") else 2,
                                              key=f"pants_size_r_{idx}", horizontal=True)
                    else:
                        pants_size = ""

                with col2:
                    thigh = st.checkbox("Thigh Pads", value=to_bool(existing.get("Thigh Pads")), key=f"thigh_r_{idx}")
                    tailbone = st.checkbox("Tailbone Pad", value=to_bool(existing.get("Tailbone Pad")), key=f"tail_r_{idx}")
                    knee = st.checkbox("Knee Pads", value=to_bool(existing.get("Knee Pads")), key=f"knee_r_{idx}")
                    secured = st.checkbox("Rental secured by Cheque or Credit Card", value=to_bool(existing.get("Secured Rental")), key=f"sec_r_{idx}")

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
                        "Secured Rental": secured,
                        "RentalDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ReturnDate": ""
                    }
                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()

    # ====================== ALL CURRENT RENTALS SUBPAGE ======================
    elif equip_sub == "All Rentals":
        st.subheader(f"📋 All Current Rentals")

        if st.button("🔄 Refresh All Rentals", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        rented_df = equipment_df.copy()
        rented_df = rented_df[rented_df.get("PlayerID", "").astype(str).str.strip() != ""]

        if not rented_df.empty:
            # Use full players_df for merge (so we get names even from previous years)
            display = rented_df.merge(
                players_df[['PlayerID', 'First Name', 'Last Name', 'Team Assignment']],
                on='PlayerID', how='left'
            )

            display['Player'] = display['First Name'].fillna("") + " " + display['Last Name'].fillna("")
            display['Team'] = display.get('Team Assignment', "").fillna("—")

            # Build readable columns
            display['Helmet'] = display.get('Helmet', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Shoulder Pads'] = display.get('Shoulder Pads', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Pants w/Belt'] = display.get('Pants w/Belt', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Thigh Pads'] = display.get('Thigh Pads', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Tailbone Pad'] = display.get('Tailbone Pad', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Knee Pads'] = display.get('Knee Pads', False).apply(lambda x: "✅" if to_bool(x) else "")
            display['Rental Date'] = display.get('RentalDate', "")

            st.dataframe(
                display[['Player', 'Team', 'Helmet', 'Shoulder Pads', 'Pants w/Belt',
                         'Thigh Pads', 'Tailbone Pad', 'Knee Pads', 'Rental Date']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No equipment is currently rented out.")

    # ====================== RETURN SUBPAGE ======================
    else:
        st.subheader(f"🔄 Return – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh Return List", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            rented_parts = []
            if to_bool(existing.get("Helmet")): rented_parts.append("Helmet")
            if to_bool(existing.get("Shoulder Pads")): rented_parts.append("Shoulder Pads")
            if to_bool(existing.get("Pants w/Belt")): rented_parts.append("Pants w/Belt")
            if to_bool(existing.get("Thigh Pads")): rented_parts.append("Thigh Pads")
            if to_bool(existing.get("Tailbone Pad")): rented_parts.append("Tailbone Pad")
            if to_bool(existing.get("Knee Pads")): rented_parts.append("Knee Pads")

            current_summary = " | ".join(rented_parts) if rented_parts else "Nothing currently rented"

            with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — Currently out: {current_summary}"):
                if not rented_parts:
                    st.info("All equipment already returned.")
                    continue

                col1, col2 = st.columns(2)
                with col1:
                    helmet_ret = st.checkbox("Return Helmet", value=True, key=f"helm_ret_{idx}") if to_bool(existing.get("Helmet")) else False
                    shoulder_ret = st.checkbox("Return Shoulder Pads", value=True, key=f"shoul_ret_{idx}") if to_bool(existing.get("Shoulder Pads")) else False
                    pants_ret = st.checkbox("Return Pants w/Belt", value=True, key=f"pants_ret_{idx}") if to_bool(existing.get("Pants w/Belt")) else False
                with col2:
                    thigh_ret = st.checkbox("Return Thigh Pads", value=True, key=f"thigh_ret_{idx}") if to_bool(existing.get("Thigh Pads")) else False
                    tail_ret = st.checkbox("Return Tailbone Pad", value=True, key=f"tail_ret_{idx}") if to_bool(existing.get("Tailbone Pad")) else False
                    knee_ret = st.checkbox("Return Knee Pads", value=True, key=f"knee_ret_{idx}") if to_bool(existing.get("Knee Pads")) else False

                if st.button("✅ Return Selected Equipment", key=f"return_btn_{idx}", type="primary"):
                    new_row = existing.to_dict() if not existing.empty else {}
                    if helmet_ret: new_row["Helmet"] = False
                    if shoulder_ret: new_row["Shoulder Pads"] = False
                    if pants_ret: new_row["Pants w/Belt"] = False
                    if thigh_ret: new_row["Thigh Pads"] = False
                    if tail_ret: new_row["Tailbone Pad"] = False
                    if knee_ret: new_row["Knee Pads"] = False
                    new_row["ReturnDate"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)

                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Equipment returned for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()
