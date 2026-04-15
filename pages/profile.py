import streamlit as st
import streamlit_authenticator as stauth


def show_profile(user_row: dict, sheet, username: str, name: str):
    st.header("👤 Profile")
    st.write(f"**Logged in as:** {name} ({username})")

    st.subheader("Edit Profile Information")
    with st.form("profile_form"):
        new_name = st.text_input("Name", value=name)
        new_email = st.text_input("Email", value=user_row.get("email", "") if user_row else "")
        new_password = st.text_input("New Password (leave blank to keep current)", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            updates = {}
            if new_name and new_name != name:
                updates["name"] = new_name
            if new_email:
                updates["email"] = new_email
            if new_password and new_password == confirm_password:
                hasher = stauth.Hasher()
                hashed = hasher.hash(new_password)
                updates["password"] = hashed

            if updates:
                row_num = [u.get("username") for u in get_worksheet_data("Users").to_dict("records")].index(username) + 2
                for col_name, value in updates.items():
                    # Simple column index lookup (adjust column numbers if your Users sheet changes)
                    col_idx = {"name": 2, "email": 3, "password": 4}.get(col_name)
                    if col_idx:
                        sheet.worksheet("Users").update_cell(row_num, col_idx, value)
                st.success("Profile updated successfully!")
                st.rerun()
            else:
                st.info("No changes made.")
