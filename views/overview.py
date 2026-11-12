import plotly.express as px
import streamlit as st

import analysis
import ui

category = st.session_state["category"]
data = ui.require_data(category)
df, has_prev = data["df"], data["prev_run"] is not None
s = analysis.summarize(df, has_prev)

if not has_prev:
    st.info("Baseline snapshot. Ranking movement and new-product detection need "
            "a collection from a second day.")

c = st.columns(5)
with c[0]:
    ui.kpi("Products tracked", s["products"],
           f"ranks {s['min_rank']}–{s['max_rank']}" + (f", gaps: {', '.join(s['gaps'])}" if s["gaps"] else ""))
with c[1]:
    ui.kpi("Median price", ui.money(s["median_price"]),
           f"{s['priced']} of {s['products']} show a price · mean {ui.money(s['mean_price'])}")
with c[2]:
    ui.kpi("Average rating",
           "—" if s["avg_rating"] is None else f"{s['avg_rating']:.2f} / 5",
           f"{s['rated']} of {s['products']} rated")
with c[3]:
    ui.kpi("Improved", s["improved"] if has_prev else "—",
           "vs previous snapshot" if has_prev else "needs 2nd day")
with c[4]:
    ui.kpi("New to observed range", s["new"] if has_prev else "—",
           "not necessarily new launches" if has_prev else "needs 2nd day")

st.write("")
left, right = st.columns(2)

with left:
    st.subheader("Top 10 by rank")
    top = df.dropna(subset=["rank"]).nsmallest(10, "rank").copy()
    top["label"] = top.apply(lambda r: f"#{int(r['rank'])} {r['title'][:42]}…", axis=1)
    fig = px.bar(top, x="price_aed", y="label", orientation="h",
                 labels={"price_aed": "Price (AED)", "label": ""},
                 hover_data={"rating": True, "reviews": True})
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Bars show listed price. Products without a price show no bar.")

with right:
    st.subheader("Price distribution")
    priced = df.dropna(subset=["price_aed"])
    if priced.empty:
        st.info("No prices available in this snapshot.")
    else:
        fig = px.histogram(priced, x="price_aed", nbins=20,
                           labels={"price_aed": "Price (AED)"})
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title="Products")
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{s['priced']} priced products, "
                   f"{ui.money(s['min_price'])} to {ui.money(s['max_price'])}.")

if has_prev:
    st.subheader("Biggest movers")
    cols = ["rank", "title", "prev_rank", "rank_change", "price_aed"]
    names = {"rank": "Rank", "title": "Product", "prev_rank": "Previous rank",
             "rank_change": "Change", "price_aed": "Price (AED)"}
    g, l = st.columns(2)
    with g:
        st.markdown("**Gainers**")
        gain = df[df["status"] == "Improved"].nlargest(5, "rank_change")
        st.dataframe(gain[cols].rename(columns=names), hide_index=True, width="stretch")
    with l:
        st.markdown("**Decliners**")
        loss = df[df["status"] == "Declined"].nsmallest(5, "rank_change")
        st.dataframe(loss[cols].rename(columns=names), hide_index=True, width="stretch")
    st.caption("Change = previous rank minus current rank (positive = moved up). "
               "Only products ranked in both snapshots are compared.")