import streamlit as st

import auth

_, mid, _ = st.columns([1, 1.2, 1])
with mid:
    st.markdown("### Sign in")
    st.caption("Enter your password to access the dashboard.")
    if auth.is_initial():
        st.info("First-time setup: leave the password empty and press Sign in. "
                "You will then be asked to set a password.")
    with st.form("login"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
    if submitted:
        ok, msg = auth.login(password)
        if ok:
            st.rerun()
        else:
            st.error(msg)