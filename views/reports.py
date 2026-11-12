import streamlit as st

import report
import ui

category = st.session_state["category"]
data = ui.require_data(category)
run = data["run"]
slug = category.lower().replace(" ", "-").replace("&", "and").replace("'", "")

st.subheader("Management PDF report")
st.write(
    "A landscape A4 report with executive summary, key figures, top 10, "
    "movement vs the previous snapshot (when one exists), the ranked list, "
    "and a limitations section."
)
full = st.checkbox("Include full ranked list", value=True)

if st.button("Generate PDF", type="primary"):
    with st.spinner("Building report…"):
        pdf = report.build_pdf(category, data, full_list=full)
    st.session_state["pdf"] = {"run": run["id"], "full": full, "bytes": pdf}

cached = st.session_state.get("pdf")
if cached and cached["run"] == run["id"] and cached["full"] == full:
    st.download_button(
        "Download PDF", cached["bytes"],
        file_name=f"amazon-ae-{slug}-{run['started_at'][:10]}.pdf",
        mime="application/pdf",
    )

st.divider()
st.subheader("Raw data")
st.download_button(
    "Download snapshot (CSV)",
    data["df"].drop(columns=["image_url"]).to_csv(index=False).encode("utf-8-sig"),
    file_name=f"amazon-ae-{slug}-{run['started_at'][:10]}.csv",
    mime="text/csv",
)