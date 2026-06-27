import streamlit as st
import pandas as pd

def show_equipment(players_df, teams_df, sheet):
    st.header("🏈 Equipment Management - St. Vital Mustangs")
    
    if players_df.empty:
        st.warning("No player data available yet.")
        return
    
    # Use consistent column names (adjust if your sheet uses different names)
    name_col = "first_name" if "first_name" in players_df.columns else "First Name"
    last_col = "last_name" if "last_name" in players_df.columns else "Last Name"
    
    # Create a safe PlayerID
    players_df = players_df.copy()
    players_df['PlayerID'] = (
        players_df[name_col].astype(str).str.strip() + "_" + 
        players_df[last_col].astype(str).str.strip()
    )
    
    st.subheader("Player Equipment Status")
    
    # Example columns you might want to track
    equipment_cols = ["Helmet", "Shoulder Pads", "Jersey", "Cleats", "Mouthguard", "Status"]
    for col in equipment_cols:
        if col not in players_df.columns:
            players_df[col] = "Not Issued"
    
    # Display editable table
    edited_df = st.data_editor(
        players_df[["PlayerID", name_col, last_col] + equipment_cols],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 Save Equipment Updates"):
        # Update the original sheet (merge back changes)
        # This is a simple way - you can make it more robust
        sheet.clear()
        sheet.update([players_df.columns.values.tolist()] + players_df.values.tolist())
        st.success("✅ Equipment updates saved to Google Sheet!")
        st.rerun()
    
    # Summary stats
    st.subheader("Equipment Summary")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Players with Full Kit", len(players_df[players_df["Status"] == "Issued"]))
    with col2:
        st.metric("Pending Issuance", len(players_df[players_df["Status"] == "Not Issued"]))
