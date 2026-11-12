import streamlit as st

import auth
from config import APP_NAME, MIN_PASSWORD_LENGTH

forced = auth.state() == "must_change"

_, mid, _ = st.columns([1, 1.4, 1])
with mid:
    st.markdown("### Set your password" if forced else "### Change password")
    if forced:
        st.warning("You must set a password before you can use the dashboard.")

    current_label = "Current password" + (" (empty on first login)" if auth.is_initial() else "")
    with st.form("change_password"):
        current = st.text_input(current_label, type="password")
        new = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Update password", type="primary", width="stretch")
    st.caption(f"At least {MIN_PASSWORD_LENGTH} characters, and different from the current password.")

    if submitted:
        ok, msg = auth.change_password(current, new, confirm)
        if ok:
            st.session_state["flash"] = (
                f"Password set. Welcome to {APP_NAME}." if forced else "Password updated."
            )
            st.session_state["goto_overview"] = True
            st.rerun()
        else:
            st.error(msg)