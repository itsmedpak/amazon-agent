import streamlit as st

import ui
from config import CATEGORIES
from database import init_db

st.set_page_config(page_title="Amazon.ae Market Intelligence",
                   page_icon="📊", layout="wide")
init_db()
ui.inject_css()

pages = st.navigation([
    st.Page("views/overview.py", title="Overview", icon="📊", default=True),
    st.Page("views/best_sellers.py", title="Best Sellers", icon="🏆"),
    st.Page("views/history.py", title="History", icon="🕒"),
    st.Page("views/reports.py", title="Reports", icon="📄"),
])

with st.sidebar:
    st.selectbox("Category", list(CATEGORIES), key="category")
    st.caption("Marketplace: Amazon.ae · Source: Best Sellers · Data: local SQLite")

pages.run()