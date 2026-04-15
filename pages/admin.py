import streamlit as st
import streamlit_authenticator as stauth
from utils.sheets import get_worksheet_data   # ← This was missing


def show_admin(sheet):
    st.header("🔧 Admin – User Management")
    users_df = get_worksheet_data("Users")

    if not users_df.empty:
        user_list = users_df["username"].tolist()
        selected_user = st.selectbox("Select User to Edit", user_list, key="admin_user_select")
        if selected_user:
            user_idx = users_df[users_df["username"] == selected_user].index[0]
            user_data = users_df.iloc[user_idx]

            st.subheader(f"Editing: {user_data.get('name', selected_user)} ({selected_user})")
            new_name = st.text_input("Name", value=user_data.get("name", ""))
            new_email = st.text_input("Email", value=user_data.get("email", ""))

            with st.form("admin_password_form"):
                new_pass = st.text_input("New Password", type="password")
                confirm_pass = st.text_input("Confirm New Password", type="password")
                if st.form_submit_button("Change Password"):
                    if new_pass and new_pass == confirm_pass:
                        hasher = stauth.Hasher()
                        hashed = hasher.hash(new_pass)
                        row_num = user_idx + 2
                        sheet.worksheet("Users").update_cell(row_num, 4, hashed)
                        st.success("Password changed successfully!")
                        st.rerun()
                    else:
                        st.error("Passwords do not match or are empty.")

            current_roles = user_data.get("roles", "").split(",") if user_data.get("roles") else []
            new_roles = st.multiselect("Roles", ["Admin", "Registrar", "Coach", "Equipment", "Restricted"], default=current_roles)

            if st.button("Save All Changes"):
                row_num = user_idx + 2
                sheet.worksheet("Users").update_cell(row_num, 2, new_name)
                sheet.worksheet("Users").update_cell(row_num, 3, new_email)
                sheet.worksheet("Users").update_cell(row_num, 5, ",".join(new_roles))
                st.success("User updated successfully!")
                st.rerun()
    else:
        st.info("No users found.")
