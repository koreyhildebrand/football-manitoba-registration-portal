import streamlit as st
import pandas as pd
import datetime
from utils.sheets import get_worksheet_data
from utils.helpers import to_bool


def show_events(sheet):
    """Events / Check-In Page – Fixed warnings + auto-refresh after save"""
    st.header("🏕️ Events & Check-In")

    WORKSHEET_NAME = "EventsRegistration"

    df = get_worksheet_data(WORKSHEET_NAME)

    if df.empty:
        st.warning(f"No data found in worksheet '{WORKSHEET_NAME}'")
        return

    # Rename columns for clean display
    rename_map = {
        "Product Form: Player Name": "Player Name",
        "Lineitem name": "Session"
    }
    df = df.rename(columns=rename_map)

    # Ensure required columns exist
    if "Player Name" not in df.columns:
        df["Player Name"] = "Unknown"
    if "Session" not in df.columns:
        df["Session"] = "Unknown"
    if "Checked In" not in df.columns:
        df["Checked In"] = False
    if "Checked In Time" not in df.columns:
        df["Checked In Time"] = ""

    # Safe boolean conversion
    df["Checked In"] = df["Checked In"].apply(to_bool)

    # ====================== SESSION FILTER ======================
    sessions = sorted(df["Session"].dropna().unique().tolist())
    session_options = ["All Sessions"] + sessions
    selected_session = st.selectbox("Filter by Session", session_options, index=0)

    if selected_session != "All Sessions":
        filtered_df = df[df["Session"] == selected_session].copy()
    else:
        filtered_df = df.copy()

    display_cols = ["Checked In", "Player Name", "Session", "Checked In Time"]
    df_display = filtered_df[display_cols].copy()

    checked_in_count = int(df_display["Checked In"].sum())
    total_players = len(df_display)
    st.subheader(f"Check-In Table ({checked_in_count} / {total_players} players checked in)")

    # Interactive data editor - fixed deprecation warning
    edited_df = st.data_editor(
        df_display,
        hide_index=True,
        width="content",                    # ← Fixed deprecation
        column_config={
            "Checked In": st.column_config.CheckboxColumn("Checked In", default=False, width=120),
            "Player Name": st.column_config.TextColumn("Player Name", disabled=True, width=280),
            "Session": st.column_config.TextColumn("Session", disabled=True, width=320),
            "Checked In Time": st.column_config.TextColumn("Checked In Time", disabled=True, width=200),
        },
        num_rows="fixed"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save Check-ins", type="primary"):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            for i in range(len(edited_df)):
                original_idx = filtered_df.index[i]
                was_checked = df.at[original_idx, "Checked In"]
                now_checked = edited_df.at[i, "Checked In"]

                df.at[original_idx, "Checked In"] = now_checked

                if now_checked and not was_checked:
                    df.at[original_idx, "Checked In Time"] = now
                elif not now_checked:
                    df.at[original_idx, "Checked In Time"] = ""

            # Save to Google Sheet
            worksheet = sheet.worksheet(WORKSHEET_NAME)
            worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

            st.success("✅ Check-ins and timestamps saved successfully!")

            # Force fresh reload of the table
            st.cache_data.clear()
            st.rerun()

    st.caption(f"✅ Showing data from worksheet: **{WORKSHEET_NAME}**")

    # Safe raw data viewer (fixed Arrow serialization error)
    with st.expander("🔍 Show full raw data (for debugging)"):
        st.dataframe(df.fillna("").astype(str), width="stretch")

    st.caption(f"✅ Showing data from worksheet: **{WORKSHEET_NAME}**")
