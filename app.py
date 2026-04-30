import streamlit as st
import pandas as pd
import datetime
import time
from utils.sheets import get_live_equipment
from utils.helpers import to_bool


def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment page – Mouth Guard is now automatically cleared on any return."""
    st.header("🛡️ Equipment Management")

    # ====================== RENTAL YEAR SELECTOR ======================
    selected_year = st.selectbox(
        "Select Rental Year",
        [2024, 2025, 2026, 2027],
        index=2,
        key="equip_year"
    )

    # ====================== SUB-PAGE BUTTONS ======================
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 Rental (Checkout)", type="primary"):
            st.session_state.equip_subpage = "Rental"
    with col2:
        if st.button("📋 All Current Rentals", type="primary"):
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

    # ====================== TEAM SELECTOR ======================
    team_list = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list, key="equip_team_filter")

    if selected_team == "All Players":
        roster = df[df.get("Team Assignment", "").notna() & (df.get("Team Assignment", "") != "")].copy()
    else:
        roster = df[df.get("Team Assignment", "") == selected_team].copy()

    # ====================== EQUIPMENT DATA ======================
    equipment_df = get_live_equipment()

    # ====================== RENTAL / RETURN PAGE ======================
    if equip_sub == "Rental":
        st.subheader(f"📦 Rental / Return – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh List", type="primary"):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            current_weight = player.get("Weight", "N/A")

            # Previous year weight
            prev_year = selected_year - 1
            prev_weight = "N/A"
            prev_players = players_df.copy()
            prev_players['PlayerID'] = (prev_players['First Name'].astype(str).str.strip() + "_" +
                                       prev_players['Last Name'].astype(str).str.strip() + "_" +
                                       prev_players['Birthdate'].astype(str).str.strip())

            if 'Timestamp' in prev_players.columns:
                prev_players['RegYear'] = pd.to_datetime(prev_players['Timestamp'], errors='coerce').dt.year
                prev_row = prev_players[(prev_players['PlayerID'] == player_id) & (prev_players['RegYear'] == prev_year)]
                if not prev_row.empty:
                    prev_weight = prev_row.iloc[0].get("Weight", "N/A")

            # Last rental sizes
            last_rental_sizes = []
            last_equip = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            if not last_equip.empty:
                last_equip = last_equip.copy()
                if 'RentalDate' in last_equip.columns:
                    last_equip['RentalDate'] = pd.to_datetime(last_equip['RentalDate'], errors='coerce')
                    last_equip = last_equip.sort_values('RentalDate', ascending=False)
                last_row = last_equip.iloc[0]

                if pd.notna(last_row.get('Helmet Size')) and str(last_row.get('Helmet Size', '')).strip() != "":
                    last_rental_sizes.append(f"Helmet {last_row.get('Helmet Size', '—')}")
                if pd.notna(last_row.get('Shoulder Pads Size')) and str(last_row.get('Shoulder Pads Size', '')).strip() != "":
                    last_rental_sizes.append(f"Shoulder {last_row.get('Shoulder Pads Size', '—')}")
                if pd.notna(last_row.get('Pants Size')) and str(last_row.get('Pants Size', '')).strip() != "":
                    last_rental_sizes.append(f"Pants {last_row.get('Pants Size', '—')}")

            prev_text = "No Information Available" if prev_weight == "N/A" and not last_rental_sizes else f"Prev {prev_year}: {prev_weight} lbs" + (f" (Last: {', '.join(last_rental_sizes)})" if last_rental_sizes else "")

            # Current rented summary
            summary_parts = []
            if to_bool(existing.get("Helmet")): summary_parts.append("Helmet ✓")
            if to_bool(existing.get("Shoulder Pads")): summary_parts.append("Shoulder Pads ✓")
            if to_bool(existing.get("Pants")): summary_parts.append("Pants ✓")
            if to_bool(existing.get("Thigh Pads")): summary_parts.append("Thigh Pads ✓")
            if to_bool(existing.get("Hip Pads")): summary_parts.append("Hip Pads ✓")
            if to_bool(existing.get("Tailbone Pad")): summary_parts.append("Tailbone Pad ✓")
            if to_bool(existing.get("Knee Pads")): summary_parts.append("Knee Pads ✓")
            if to_bool(existing.get("Mouth Guard")): summary_parts.append("Mouth Guard ✓")
            if to_bool(existing.get("Belt")): summary_parts.append("Belt ✓")
            if to_bool(existing.get("Practice Jersey Red")): summary_parts.append("Red Jersey ✓")
            if to_bool(existing.get("Practice Jersey Black")): summary_parts.append("Black Jersey ✓")
            if to_bool(existing.get("Practice Jersey White")): summary_parts.append("White Jersey ✓")
            current_rented = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

            summary_line = f"Weight: {current_weight} lbs | {current_rented} | **{prev_text}**"

            with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_line}"):
                rental_date = existing.get("RentalDate", "")
                return_date = existing.get("ReturnDate", "")
                if rental_date:
                    st.markdown(f"**Rental Date:** {rental_date}")
                if return_date:
                    st.markdown(f"**Return Date:** {return_date}")

                col1, col2 = st.columns([3, 2])
                with col1:
                    helmet = st.checkbox("Helmet", value=to_bool(existing.get("Helmet")), key=f"helm_r_{idx}")
                    if helmet:
                        helmet_type = st.text_input("Helmet Type", value=existing.get("Helmet Type", ""), key=f"helm_type_r_{idx}")
                        helmet_year = st.text_input("Helmet Year", value=existing.get("Helmet Year", ""), key=f"helm_year_r_{idx}")
                        helmet_size = st.radio("Helmet Size", ["XS", "S", "M", "L", "XL", "XXL", "AS", "AM", "AL", "AXL"], key=f"helm_size_r_{idx}", horizontal=True)
                    else:
                        helmet_type = helmet_year = helmet_size = ""

                    shoulder = st.checkbox("Shoulder Pads", value=to_bool(existing.get("Shoulder Pads")), key=f"shoul_r_{idx}")
                    if shoulder:
                        shoulder_type = st.text_input("Shoulder Pads Type", value=existing.get("Shoulder Pads Type", ""), key=f"shoul_type_r_{idx}")
                        shoulder_size = st.radio("Shoulder Size", ["XS", "S", "M", "L", "XL", "XXL"], key=f"shoul_size_r_{idx}", horizontal=True)
                    else:
                        shoulder_type = shoulder_size = ""

                    pants = st.checkbox("Pants", value=to_bool(existing.get("Pants")), key=f"pants_r_{idx}")
                    if pants:
                        pants_size = st.radio("Pants Size", ["YXS", "YS", "YM", "YL", "YXL", "YXXL", "AS", "AM", "AL", "AXL", "A2XL", "A3XL"], key=f"pants_size_r_{idx}", horizontal=True)
                    else:
                        pants_size = ""

                with col2:
                    thigh = st.checkbox("Thigh Pads", value=to_bool(existing.get("Thigh Pads")), key=f"thigh_r_{idx}")
                    hip_pads = st.checkbox("Hip Pads", value=to_bool(existing.get("Hip Pads")), key=f"hip_r_{idx}")
                    tailbone = st.checkbox("Tailbone Pad", value=to_bool(existing.get("Tailbone Pad")), key=f"tail_r_{idx}")
                    knee = st.checkbox("Knee Pads", value=to_bool(existing.get("Knee Pads")), key=f"knee_r_{idx}")
                    mouth_guard = st.checkbox("Mouth Guard", value=to_bool(existing.get("Mouth Guard")), key=f"mouth_r_{idx}")
                    belt = st.checkbox("Belt", value=to_bool(existing.get("Belt")), key=f"belt_r_{idx}")

                    # Practice Jerseys
                    st.markdown("**Practice Jerseys**")
                    red_jersey = st.checkbox("Practice Jersey Red", value=to_bool(existing.get("Practice Jersey Red")), key=f"red_jersey_r_{idx}")
                    if red_jersey:
                        red_size = st.radio("Red Jersey Size", ["Y S/M", "Y L/XL", "S/M", "L/XL", "2XL/3XL"], key=f"red_size_r_{idx}", horizontal=True)
                    else:
                        red_size = ""

                    black_jersey = st.checkbox("Practice Jersey Black", value=to_bool(existing.get("Practice Jersey Black")), key=f"black_jersey_r_{idx}")
                    if black_jersey:
                        black_size = st.radio("Black Jersey Size", ["Y S/M", "Y L/XL", "S/M", "L/XL", "2XL/3XL"], key=f"black_size_r_{idx}", horizontal=True)
                    else:
                        black_size = ""

                    white_jersey = st.checkbox("Practice Jersey White", value=to_bool(existing.get("Practice Jersey White")), key=f"white_jersey_r_{idx}")
                    if white_jersey:
                        white_size = st.radio("White Jersey Size", ["Y S/M", "Y L/XL", "S/M", "L/XL", "2XL/3XL"], key=f"white_size_r_{idx}", horizontal=True)
                    else:
                        white_size = ""

                    secured_options = ["Cheque", "Credit Card", "Cash", "Debit"]
                    secured_default = existing.get("Secured Rental", "Cheque")
                    if secured_default not in secured_options:
                        secured_default = "Cheque"
                    secured = st.radio("Rental Secured by", secured_options, index=secured_options.index(secured_default), key=f"sec_r_{idx}")

                    waiver = st.checkbox("Parent Signed Waiver", value=to_bool(existing.get("Parent Signed Waiver")), key=f"waiver_r_{idx}")

                # Save Rental
                if st.button("💾 Save Rental for this Player", key=f"save_rental_{idx}", type="primary"):
                    new_row = {
                        "PlayerID": player_id,
                        "First Name": player.get("First Name", ""),
                        "Last Name": player.get("Last Name", ""),
                        "Helmet": helmet, "Helmet Type": helmet_type if helmet else "", "Helmet Year": helmet_year if helmet else "", "Helmet Size": helmet_size if helmet else "",
                        "Shoulder Pads": shoulder, "Shoulder Pads Type": shoulder_type if shoulder else "", "Shoulder Pads Size": shoulder_size if shoulder else "",
                        "Pants": pants, "Pants Size": pants_size if pants else "",
                        "Thigh Pads": thigh, "Hip Pads": hip_pads, "Tailbone Pad": tailbone, "Knee Pads": knee,
                        "Mouth Guard": mouth_guard, "Belt": belt,
                        "Practice Jersey Red": red_jersey, "Practice Jersey Red Size": red_size if red_jersey else "",
                        "Practice Jersey Black": black_jersey, "Practice Jersey Black Size": black_size if black_jersey else "",
                        "Practice Jersey White": white_jersey, "Practice Jersey White Size": white_size if white_jersey else "",
                        "Secured Rental": secured, "Parent Signed Waiver": waiver,
                        "RentalDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ReturnDate": ""
                    }
                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()

                # ====================== RETURN SECTION ======================
                has_active_rental = any(to_bool(existing.get(col)) for col in ["Helmet","Shoulder Pads","Pants","Thigh Pads","Hip Pads","Tailbone Pad","Knee Pads","Mouth Guard","Belt","Practice Jersey Red","Practice Jersey Black","Practice Jersey White"])
                if has_active_rental and not return_date:
                    st.markdown("---")
                    st.subheader("🔄 Return Equipment")
                    col_ret1, col_ret2 = st.columns(2)
                    with col_ret1:
                        helmet_ret = st.checkbox("Return Helmet", value=True, key=f"helm_ret_{idx}") if to_bool(existing.get("Helmet")) else False
                        shoulder_ret = st.checkbox("Return Shoulder Pads", value=True, key=f"shoul_ret_{idx}") if to_bool(existing.get("Shoulder Pads")) else False
                        pants_ret = st.checkbox("Return Pants", value=True, key=f"pants_ret_{idx}") if to_bool(existing.get("Pants")) else False
                        red_ret = st.checkbox("Return Practice Jersey Red", value=True, key=f"red_ret_{idx}") if to_bool(existing.get("Practice Jersey Red")) else False
                        black_ret = st.checkbox("Return Practice Jersey Black", value=True, key=f"black_ret_{idx}") if to_bool(existing.get("Practice Jersey Black")) else False
                        white_ret = st.checkbox("Return Practice Jersey White", value=True, key=f"white_ret_{idx}") if to_bool(existing.get("Practice Jersey White")) else False
                    with col_ret2:
                        thigh_ret = st.checkbox("Return Thigh Pads", value=True, key=f"thigh_ret_{idx}") if to_bool(existing.get("Thigh Pads")) else False
                        hip_ret = st.checkbox("Return Hip Pads", value=True, key=f"hip_ret_{idx}") if to_bool(existing.get("Hip Pads")) else False
                        tail_ret = st.checkbox("Return Tailbone Pad", value=True, key=f"tail_ret_{idx}") if to_bool(existing.get("Tailbone Pad")) else False
                        knee_ret = st.checkbox("Return Knee Pads", value=True, key=f"knee_ret_{idx}") if to_bool(existing.get("Knee Pads")) else False
                        belt_ret = st.checkbox("Return Belt", value=True, key=f"belt_ret_{idx}") if to_bool(existing.get("Belt")) else False

                    if st.button("✅ Return Selected Equipment", key=f"return_btn_{idx}", type="primary"):
                        new_row = existing.to_dict() if not existing.empty else {}
                        if helmet_ret: new_row["Helmet"] = False
                        if shoulder_ret: new_row["Shoulder Pads"] = False
                        if pants_ret: new_row["Pants"] = False
                        if thigh_ret: new_row["Thigh Pads"] = False
                        if hip_ret: new_row["Hip Pads"] = False
                        if tail_ret: new_row["Tailbone Pad"] = False
                        if knee_ret: new_row["Knee Pads"] = False
                        if belt_ret: new_row["Belt"] = False
                        if red_ret: new_row["Practice Jersey Red"] = False
                        if black_ret: new_row["Practice Jersey Black"] = False
                        if white_ret: new_row["Practice Jersey White"] = False
                        
                        # 🔥 NEW: Automatically clear Mouth Guard on any return
                        new_row["Mouth Guard"] = False

                        new_row["ReturnDate"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                        equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                        equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                        sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                        st.success(f"✅ Equipment returned for {player.get('First Name')} {player.get('Last Name')}")
                        time.sleep(0.5)
                        st.rerun()

    # ====================== ALL CURRENT RENTALS ======================
    elif equip_sub == "All Rentals":
        st.subheader(f"📋 All Current Rentals")
        if st.button("🔄 Refresh All Rentals", type="primary"):
            st.cache_data.clear()
            st.rerun()

        rented_df = equipment_df.copy()
        rented_df = rented_df[rented_df.get("PlayerID", "").astype(str).str.strip() != ""]
        rented_df = rented_df[
            pd.isna(rented_df.get("ReturnDate")) | 
            (rented_df.get("ReturnDate", "").astype(str).str.strip() == "")
        ]

        if not rented_df.empty:
            display = rented_df.merge(
                df[['PlayerID', 'First Name', 'Last Name', 'Team Assignment']],
                on='PlayerID', how='left'
            )

            first = display.get('First Name', pd.Series([""] * len(display))).fillna("")
            last  = display.get('Last Name',  pd.Series([""] * len(display))).fillna("")
            display['Player'] = (first + " " + last).str.strip()
            display['Player'] = display['Player'].where(display['Player'] != "", display.get('PlayerID', "Unknown Player"))

            display['Team'] = display.get('Team Assignment', pd.Series(["—"] * len(display))).fillna("—")

            for col in ['Helmet', 'Shoulder Pads', 'Pants', 'Thigh Pads', 'Hip Pads', 'Tailbone Pad', 'Knee Pads', 'Mouth Guard', 'Belt']:
                if col in display.columns:
                    display[col] = display[col].apply(lambda x: "✅" if to_bool(x) else "")
                else:
                    display[col] = ""

            display['Rental Date'] = display.get('RentalDate', "")

            st.subheader("Total Equipment Currently Out")
            total_row = {col: (display[col] == "✅").sum() for col in ['Helmet', 'Shoulder Pads', 'Pants', 'Thigh Pads', 'Hip Pads', 'Tailbone Pad', 'Knee Pads', 'Mouth Guard', 'Belt']}
            st.dataframe(pd.DataFrame([total_row]), hide_index=True, use_container_width=True)

            st.subheader("Equipment by Team")
            team_totals = display.groupby('Team').agg({col: lambda x: (x == "✅").sum() for col in ['Helmet', 'Shoulder Pads', 'Pants', 'Thigh Pads', 'Hip Pads', 'Tailbone Pad', 'Knee Pads', 'Mouth Guard', 'Belt']}).reset_index()
            st.dataframe(team_totals, hide_index=True, use_container_width=True)

            st.subheader("All Rented Equipment")
            st.dataframe(
                display[['Player', 'Team', 'Helmet', 'Shoulder Pads', 'Pants', 'Thigh Pads', 'Hip Pads',
                         'Tailbone Pad', 'Knee Pads', 'Mouth Guard', 'Belt', 'Rental Date']].sort_values('Team'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No equipment is currently rented out.")

    st.caption(f"✅ St. Vital Mustangs Registration Portal | v4.00")
