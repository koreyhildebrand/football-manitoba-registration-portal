import streamlit as st
import pandas as pd
import datetime


def show_events(events_df: pd.DataFrame, events_reg_df: pd.DataFrame, sheet, filter_by_team_func, can_see_all_teams: bool, allowed_teams: list):
    st.header("🏕️ Events – Registered Participants & Check-In")

    if st.button("🔄 Refresh Events & Registrations", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    df_filtered = filter_by_team_func(events_reg_df.copy(), can_see_all_teams, allowed_teams)

    event_name_col = next((col for col in ["EventName", "Name", "Event"] if col in events_df.columns), None)
    if not events_df.empty and event_name_col:
        event_list = events_df[event_name_col].dropna().unique().tolist()
        if event_list:
            selected_event = st.selectbox("Select Event", event_list, key="event_selector")
            if selected_event:
                reg_event_col = next((col for col in ["EventName", "Name", "Event"] if col in df_filtered.columns), None)
                filtered_reg = df_filtered[df_filtered[reg_event_col] == selected_event].copy() if reg_event_col else df_filtered.copy()

                if not filtered_reg.empty:
                    st.subheader(f"Registrations for: {selected_event}")
                    if "CheckIn" not in filtered_reg.columns:
                        filtered_reg["CheckIn"] = False
                    if "CheckInTime" not in filtered_reg.columns:
                        filtered_reg["CheckInTime"] = ""

                    name_col = next((col for col in ["First Name", "Last Name", "Name", "Player Name"] if col in filtered_reg.columns), None)
                    if name_col and "First Name" in filtered_reg.columns and "Last Name" in filtered_reg.columns:
                        filtered_reg["Player Name"] = filtered_reg["First Name"].astype(str) + " " + filtered_reg["Last Name"].astype(str)

                    edited_reg = st.data_editor(
                        filtered_reg,
                        num_rows="dynamic",
                        width='stretch',
                        column_config={
                            "CheckIn": st.column_config.CheckboxColumn("Checked In", default=False, width="small"),
                            "CheckInTime": st.column_config.TextColumn("Check-In Time", disabled=True)
                        },
                        key="events_checkin_editor"
                    )

                    if st.button("💾 Save Check-In Changes", type="primary"):
                        for i, row in edited_reg.iterrows():
                            if row.get("CheckIn") is True and not row.get("CheckInTime"):
                                edited_reg.at[i, "CheckInTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        sheet.worksheet("EventsRegistration").update([edited_reg.columns.values.tolist()] + edited_reg.fillna("").values.tolist())
                        st.success("✅ Check-in data saved!")
                else:
                    st.info(f"No registrations yet for '{selected_event}'.")
        else:
            st.info("No events have been created yet.")
    else:
        st.warning("No events found. Please create events in Registrar → Event Creation first.")
