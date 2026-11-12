import pandas as pd
import plotly.express as px
import streamlit as st

import analysis
import ui
from database import run_stats

category = st.session_state["category"]
data = ui.require_data(category)

st.subheader("Collection runs")
runs = pd.DataFrame(analysis.all_runs(category))
runs["Collected"] = runs["started_at"].map(analysis.fmt_ts)
st.dataframe(
    runs[["Collected", "status", "pages_ok", "pages_requested", "product_count",
          "page_heading", "message"]].rename(columns={
        "status": "Status", "pages_ok": "Pages OK", "pages_requested": "Pages requested",
        "product_count": "Products", "page_heading": "Page heading", "message": "Warnings"}),
    hide_index=True, width="stretch",
)
st.caption("Trend analysis uses one COMPLETED run per day (the latest). "
           "Extra runs on the same day are kept here but not counted as snapshots.")

with st.expander("Data quality, latest 30 runs across all categories"):
    dq = pd.DataFrame(run_stats())
    if not dq.empty:
        dq["started_at"] = dq["started_at"].map(analysis.fmt_ts)
        st.dataframe(dq, hide_index=True, width="stretch")
    st.caption("null_* columns count products where that field was not found on the page.")

st.subheader("Product history")
df = data["df"].sort_values("rank")
labels = {r.asin: f"#{int(r.rank)} · {r.title[:70]}" for r in df.itertuples()}
asin = st.selectbox("Product", list(labels), format_func=lambda a: labels[a])
hist = analysis.product_history(asin, category)

if len(hist) < 2:
    st.info(f"Only {len(hist)} daily snapshot for this product. "
            "Charts appear once there are at least two.")
else:
    a, b = st.columns(2)
    with a:
        fig = px.line(hist, x="date", y="rank", markers=True, title="Rank (lower is better)")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch")
    with b:
        fig = px.line(hist, x="date", y="price_aed", markers=True, title="Price (AED)")
        st.plotly_chart(fig, width="stretch")
st.dataframe(hist.drop(columns=["started_at"]), hide_index=True, width="stretch")