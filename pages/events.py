import streamlit as st
import pandas as pd
from utils.sheets import get_worksheet_data


def show_events(sheet):
    """Events / Check-In Page – Uses EventsRegistration worksheet"""
    st.header("🏕️ Events & Check-In")

    # ====================== WORKSHEET NAME ======================
    WORKSHEET_NAME = "EventsRegistration"   # ← Correct name as you requested
    # ============================================================

    df = get_worksheet_data(WORKSHEET_NAME)

    if df.empty:
        st.warning(f"No data found in worksheet '{WORKSHEET_NAME}'")
        return

    # Rename columns for clean display (exactly as you requested)
    rename_map = {
        "Product Form: Player Name": "Player Name",
        "Lineitem name": "Session"
    }
    df = df.rename(columns=rename_map)

    # Keep only the columns we want + add Checked In column if missing
    display_cols = ["Player Name", "Session"]
    if "Checked In" not in df.columns:
        df["Checked In"] = False

    df_display = df[display_cols + ["Checked In"]].copy()

    st.subheader("Check-In Table")

    # Interactive data editor
    edited_df = st.data_editor(
        df_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Player Name": st.column_config.TextColumn("Player Name", disabled=True),
            "Session": st.column_config.TextColumn("Session", disabled=True),
            "Checked In": st.column_config.CheckboxColumn("Checked In", default=False),
        },
        num_rows="fixed"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save Check-ins", type="primary"):
            # Merge the edited Checked In values back
            df["Checked In"] = edited_df["Checked In"]

            # Write back to Google Sheet
            worksheet = sheet.worksheet(WORKSHEET_NAME)
            worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

            st.success("✅ Check-ins saved successfully!")
            st.rerun()

    st.caption(f"✅ Showing data from worksheet: **{WORKSHEET_NAME}**")

    # Optional raw data viewer
    with st.expander("🔍 Show full raw data (for debugging)"):
        st.dataframe(df, use_container_width=True)
