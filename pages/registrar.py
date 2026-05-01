import streamlit as st
import pandas as pd
import datetime
from utils.helpers import calculate_age_group, filter_by_team


def show_registrar(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet, events_df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list):
    """Registrar page – Now filtered to selected year across all tabs."""
    st.header("📋 Registrar")

    # ====================== DYNAMIC YEAR SELECTOR ======================
    if 'Timestamp' in players_df.columns and not players_df.empty:
        temp = players_df.copy()
        temp['RegYear'] = pd.to_datetime(temp['Timestamp'], errors='coerce').dt.year
        current_year = int(temp['RegYear'].max()) if not temp['RegYear'].isna().all() else datetime.datetime.now().year
    else:
        current_year = datetime.datetime.now().year

    selected_year = st.selectbox(
        "Select Season Year",
        [2024, 2025, 2026, 2027],
        index=[2024, 2025, 2026, 2027].index(current_year) if current_year in [2024, 2025, 2026, 2027] else 2,
        key="registrar_year_select"
    )

    # ====================== SUB-PAGE BUTTONS ======================
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        if st.button("📊 Dashboard", key="reg_dashboard", width='stretch'):
            st.session_state.reg_subpage = "Dashboard"
    with sub_col2:
        if st.button("👥 Team Assignments", key="reg_assign", width='stretch'):
            st.session_state.reg_subpage = "Team Assignments"
    with sub_col3:
        if st.button("👥 Players", key="reg_players", width='stretch'):
            st.session_state.reg_subpage = "Players"

    if "reg_subpage" not in st.session_state:
        st.session_state.reg_subpage = "Dashboard"
    subpage = st.session_state.reg_subpage

    # ====================== FILTER TO SELECTED YEAR ======================
    df_filtered = filter_by_team(players_df.copy(), can_see_all_teams, allowed_teams)

    # Apply year filter
    df = df_filtered.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    if subpage == "Dashboard":
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

    elif subpage == "Team Assignments":
        st.subheader("👥 Team Assignments")
        if st.button("🔄 Refresh Teams & Players", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()
        
        show_unassigned = st.toggle("Show only players not assigned to a team", value=True, key="unassigned_toggle")
        available_players = df[df.get("Team Assignment", "").isna() | (df.get("Team Assignment", "") == "")] if show_unassigned else df
        
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
        
        df_to_show = df.copy()
        
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
        st.caption(f"Showing {len(df_to_show)} players in {selected_year}")

    st.caption(f"✅ St. Vital Mustangs Registration Portal | Registrar – {selected_year} Season")
