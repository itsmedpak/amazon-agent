import pandas as pd
import streamlit as st

import analysis

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
.kpi {border: 1px solid rgba(128,128,128,.28); border-radius: 12px;
      padding: 14px 16px; background: rgba(128,128,128,.06);}
.kpi-label {font-size: .75rem; text-transform: uppercase;
            letter-spacing: .05em; opacity: .7;}
.kpi-value {font-size: 1.75rem; font-weight: 700; line-height: 1.3;}
.kpi-note {font-size: .78rem; opacity: .65; min-height: 1.1em;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def money(v):
    return "—" if v is None or pd.isna(v) else f"AED {v:,.2f}"


def kpi(label, value, note=""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def header(category, data):
    st.title(category)
    if data is None:
        st.caption("Amazon.ae Best Sellers · no data collected yet")
        return
    run = data["run"]
    st.caption(
        f"Amazon.ae Best Sellers · collected {analysis.fmt_ts(run['started_at'])} · "
        f"{run['product_count']} products · {data['snapshots']} daily snapshot(s) · "
        f"page: {run.get('page_heading') or 'n/a'}"
    )


def require_data(category):
    data = analysis.load_view(category)
    header(category, data)
    if data is None:
        st.info(
            f"No completed collection for **{category}** yet. Run "
            f'`python collect.py --category "{category}"` in a terminal.'
        )
        st.stop()
    return data