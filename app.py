import streamlit as st

import auth
import ui
from config import APP_NAME, CATEGORIES
from database import init_db

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide")
init_db()
auth.init_auth()
ui.inject_css()
ui.render_header()
ui.render_footer()

login_page = st.Page("views/login.py", title="Sign in", icon="🔐", url_path="login")
password_page = st.Page("views/change_password.py", title="Change password",
                        icon="🔑", url_path="change-password")
overview_page = st.Page("views/overview.py", title="Overview", icon="📊", default=True)

state = auth.state()

if state == "logged_out":
    nav = st.navigation([login_page], position="hidden")
elif state == "must_change":
    nav = st.navigation([password_page], position="hidden")   # nothing else reachable
else:
    nav = st.navigation({
        "Analytics": [
            overview_page,
            st.Page("views/best_sellers.py", title="Best Sellers", icon="🏆"),
            st.Page("views/history.py", title="History", icon="🕒"),
            st.Page("views/reports.py", title="Reports", icon="📄"),
        ],
        "Account": [password_page],
    })
    with st.sidebar:
        st.selectbox("Category", list(CATEGORIES), key="category")
        st.caption("Marketplace: Amazon.ae · Source: Best Sellers")
        if st.button("Sign out", width="stretch"):
            auth.logout()
            st.rerun()
    # After a successful password change, go to Overview.
    if st.session_state.pop("goto_overview", False):
        st.switch_page(overview_page)

# Pop the flash only after the redirect so the toast survives the page switch.
flash = st.session_state.pop("flash", None)
if flash:
    st.toast(flash)

nav.run()