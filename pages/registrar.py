import streamlit as st
import pandas as pd
import datetime
from utils.helpers import calculate_age_group, filter_by_team


def show_registrar(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet, events_df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list):
    """Registrar page – updated birth-year logic (your exact spec)."""
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

    df_filtered = filter_by_team(players_df.copy(), can_see_all_teams, allowed_teams)

    if subpage == "Dashboard":
        df = df_filtered.copy()
        df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                          df['Last Name'].astype(str).str.strip() + "_" +
                          df['Birthdate'].astype(str).str.strip())

        if 'Timestamp' in df.columns:
            df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
            df = df[df['RegYear'] == selected_year]
            df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

        df['AgeGroup'] = df['Birthdate'].apply(lambda x: calculate_age_group(x, selected_year))
        df['BirthYear'] = pd.to_datetime(df['Birthdate'], errors='coerce').dt.year

        st.subheader(f"Registered Players – {selected_year} Season")
        cols = st.columns(6)
        age_groups = ['U10', 'U12', 'U14', 'U16', 'U18', 'Major']
        for i, ag in enumerate(age_groups):
            group_df = df[df['AgeGroup'] == ag]
            total = len(group_df)
            if ag != 'Major' and not group_df.empty:
                base = int(ag[1:])
                year1_birth = selected_year - (base - 2)
                year2_birth = selected_year - (base - 1)
                y1 = len(group_df[group_df['BirthYear'] == year1_birth])
                y2 = len(group_df[group_df['BirthYear'] == year2_birth])
                # UPDATED: Clean format you requested
                breakdown = f" (Y1: {y1}, Y2: {y2})"
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

    # === Team Assignments, Players, Event Creation (unchanged) ===
    elif subpage == "Team Assignments":
        st.subheader("👥 Team Assignments")
        if st.button("🔄 Refresh Teams & Players", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")
        available_players = df_filtered[df_filtered.get("Team Assignment", "").isna() | (df_filtered.get("Team Assignment", "") == "")] if show_unassigned else df_filtered

        player_list = (available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str)).tolist()
        p_sel = st.selectbox("Select Player", player_list, key="assign_player") if player_list else None

        if p_sel:
            idx = available_players.index[available_players["First Name"].astype(str) + " " + available_players["Last Name"].astype(str) == p_sel][0]
            player_row = players_df.iloc[idx]

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

            matching_teams = teams_df[teams_df.get("Division", "").str.strip() == player_age_group]["TeamName"].tolist() if not teams_df.empty else []

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
                    if st.form_submit_button("Create Team & Assign Player"):
                        if new_team_name:
                            new_team_row = {"TeamName": new_team_name, "Division": player_age_group, "Coach": new_coach if new_coach else ""}
                            teams_df = pd.concat([teams_df, pd.DataFrame([new_team_row])], ignore_index=True)
                            sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
                            players_df.at[idx, "Team Assignment"] = new_team_name
                            sheet.worksheet("Players").update([players_df.columns.values.tolist()] + players_df.fillna("").values.tolist())
                            st.success(f"✅ New team '{new_team_name}' created and {p_sel} assigned!")
                            st.rerun()

    elif subpage == "Players":
        st.subheader("👥 All Registered Players")
        if st.button("🔄 Refresh Roster", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        df_to_show = df_filtered.copy()
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else ["All Teams"]
        selected_team_filter = st.selectbox("Filter by Assigned Team", team_options, key="players_team_filter")
        if selected_team_filter != "All Teams":
            df_to_show = df_to_show[df_to_show.get("Team Assignment", "") == selected_team_filter]

        search = st.text_input("🔍 Search players", key="reg_players_search")
        if search:
            df_to_show = df_to_show[df_to_show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        display_cols = ["First Name", "Last Name", "AgeGroup", "Contact Phone Number", "Email", "Team Assignment"]
        available_cols = [c for c in display_cols if c in df_to_show.columns]
        st.dataframe(df_to_show[available_cols], width='stretch', hide_index=True)
        st.caption(f"Showing {len(df_to_show)} players")

    elif subpage == "Event Creation":
        st.subheader("📅 Upcoming & Ongoing Events")
        if st.button("🔄 Refresh Events List", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        if not events_df.empty:
            st.dataframe(events_df, width='stretch')
        else:
            st.info("No events created yet.")

        st.subheader("Create New Event")
        e_name = st.text_input("Event Name", key="event_name")
        col1, col2 = st.columns(2)
        with col1:
            e_start_date = st.date_input("Start Date", key="e_start_date")
            e_start_time = st.time_input("Start Time", key="e_start_time", value=datetime.time(9, 0))
        with col2:
            e_end_date = st.date_input("End Date", key="e_end_date")
            e_end_time = st.time_input("End Time", key="e_end_time", value=datetime.time(16, 0))
        e_max = st.number_input("Max Participants", min_value=1, value=40, key="event_max")
        e_location = st.text_input("Location", key="event_location")
        e_desc = st.text_area("Description", key="event_desc")
        if st.button("Create New Event", key="create_event"):
            new_event = {
                "EventID": len(events_df) + 1,
                "EventName": e_name,
                "Start Date": str(e_start_date),
                "End Date": str(e_end_date),
                "Start Time": str(e_start_time),
                "End Time": str(e_end_time),
                "Location": e_location,
                "Description": e_desc,
                "MaxPlayers": e_max
            }
            events_df = pd.concat([events_df, pd.DataFrame([new_event])], ignore_index=True)
            sheet.worksheet("Events").update([events_df.columns.values.tolist()] + events_df.fillna("").values.tolist())
            st.success(f"✅ Event '{e_name}' created!")
            st.rerun()
