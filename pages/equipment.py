import streamlit as st
import pandas as pd
from utils.sheets import get_live_equipment
from utils.helpers import to_bool


def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment Rental & Return page with Rental Year filter."""
    st.header("🛡️ Equipment Management")

    # ====================== RENTAL YEAR SELECTOR ======================
    selected_year = st.selectbox(
        "Select Rental Year",
        [2024, 2025, 2026, 2027],
        index=2,
        key="equip_year"
    )

    if st.button("🔄 Refresh All Equipment Data", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    # Sub-page selector
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

    # ====================== FILTER PLAYERS BY SELECTED YEAR ======================
    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # ====================== TEAM SELECTOR ======================
    team_options = sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else []
    if not team_options:
        st.warning("No teams exist yet.")
        st.stop()

    selected_team = st.selectbox("Select Team", team_options, key="equip_team_filter")

    # Use the year-filtered dataframe
    roster = df[df.get("Team Assignment", "") == selected_team].copy()

    # ====================== EQUIPMENT DATA ======================
    equipment_df = get_live_equipment()

    if equip_sub == "Rental":
        st.subheader(f"📦 Rental – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh Rental List", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            summary_parts = []
            if to_bool(existing.get("Helmet")): summary_parts.append("Helmet ✓")
            if to_bool(existing.get("Shoulder Pads")): summary_parts.append("Shoulder Pads ✓")
            if to_bool(existing.get("Pants w/Belt")): summary_parts.append("Pants w/Belt ✓")
            if to_bool(existing.get("Thigh Pads")): summary_parts.append("Thigh Pads ✓")
            if to_bool(existing.get("Tailbone Pad")): summary_parts.append("Tailbone Pad ✓")
            if to_bool(existing.get("Knee Pads")): summary_parts.append("Knee Pads ✓")
            summary_text = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

            with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_text}"):
                col1, col2 = st.columns([3, 2])
                with col1:
                    helmet = st.checkbox("Helmet", value=to_bool(existing.get("Helmet")), key=f"helm_r_{idx}")
                    helmet_size = st.selectbox("Helmet Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not helmet, key=f"helm_size_r_{idx}")
                    shoulder = st.checkbox("Shoulder Pads", value=to_bool(existing.get("Shoulder Pads")), key=f"shoul_r_{idx}")
                    shoulder_size = st.selectbox("Shoulder Pads Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not shoulder, key=f"shoul_size_r_{idx}")
                    pants = st.checkbox("Pants w/Belt", value=to_bool(existing.get("Pants w/Belt")), key=f"pants_r_{idx}")
                    pants_size = st.selectbox("Pants Size", ["", "XS", "S", "M", "L", "XL", "XXL"], disabled=not pants, key=f"pants_size_r_{idx}")
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
                        "Secured Rental": secured
                    }
                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()

    elif equip_sub == "Return":
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

                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)

                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Equipment returned for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()
