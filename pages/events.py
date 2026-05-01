import streamlit as st
import pandas as pd
from utils.sheets import get_worksheet_data


def show_events(sheet):
    """Events / Check-In Page – Clean view with Player Name, Session, and CheckIn checkbox."""
    st.header("📅 Events & Check-In")

    # ====================== CHANGE THIS IF YOUR WORKSHEET HAS A DIFFERENT NAME ======================
    WORKSHEET_NAME = "Orders"          # ←←← Change this if needed (e.g. "Shopify Orders", "Event Orders")
    # ===============================================================================================

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

    # Keep only the columns we want + add Checked In if missing
    display_cols = ["Player Name", "Session"]
    if "Checked In" not in df.columns:
        df["Checked In"] = False

    # Reorder and keep only what we need for the editor
    df_display = df[display_cols + ["Checked In"]].copy()

    st.subheader("Check-In Table")

    # Interactive editor
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
            # Merge the edited Checked In values back into the original dataframe
            df["Checked In"] = edited_df["Checked In"]

            # Write back to Google Sheet
            worksheet = sheet.worksheet(WORKSHEET_NAME)
            worksheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

            st.success("✅ Check-ins saved successfully!")
            st.rerun()

    st.caption(f"✅ Showing data from worksheet: **{WORKSHEET_NAME}**")

    # Optional: show raw data for debugging
    with st.expander("🔍 Show full raw data (for debugging)"):
        st.dataframe(df, use_container_width=True)
