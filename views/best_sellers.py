from html import escape

import streamlit as st

import ui

category = st.session_state["category"]
data = ui.require_data(category)
df, has_prev = data["df"], data["prev_run"] is not None

f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
query = f1.text_input("Search product", placeholder="e.g. sofa, desk, shelf")
min_rating = f2.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)
only_priced = f3.checkbox("Only products with a price", value=False)
statuses = f4.multiselect("Movement", sorted(df["status"].unique())) if has_prev else []

SORTS = {"Rank": "rank", "Price": "price_aed", "Rating": "rating", "Ratings count": "reviews"}
if has_prev:
    SORTS["Rank change"] = "rank_change"
s1, s2, _ = st.columns([2, 2, 4])
sort_label = s1.selectbox("Sort by", list(SORTS))
descending = s2.radio("Order", ["Ascending", "Descending"], horizontal=True) == "Descending"

view = df.copy()
if query:
    view = view[view["title"].str.contains(query, case=False, na=False)]
if min_rating > 0:
    view = view[view["rating"] >= min_rating]  # unrated products are excluded
if only_priced:
    view = view[view["price_aed"].notna()]
if statuses:
    view = view[view["status"].isin(statuses)]
view = view.sort_values(SORTS[sort_label], ascending=not descending, na_position="last")

st.caption(f"Showing {len(view)} of {len(df)} products. Hover an image to enlarge it.")

table_tab, cards_tab = st.tabs(["Table", "Cards"])

with table_tab:
    st.markdown(ui.product_table_html(view, has_prev), unsafe_allow_html=True)
    st.write("")
    st.download_button(
        "Download filtered list (CSV)",
        view.drop(columns=["image_url"]).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"best-sellers-{category.lower().replace(' ', '-')}.csv",
        mime="text/csv",
    )

with cards_tab:
    shown = view.head(12)
    for start in range(0, len(shown), 4):
        cols = st.columns(4)
        for col, p in zip(cols, shown.iloc[start:start + 4].itertuples()):
            with col, st.container(border=True):
                st.markdown(ui.thumb_html(p.image_url, size=150, center=True),
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="card-title"><b>#{ui.num(p.rank, "{:,.0f}")}</b> '
                    f"{escape(str(p.title)[:80])}</div>",
                    unsafe_allow_html=True,
                )
                rating = "no rating" if p.rating != p.rating else f"{p.rating:.1f} ★"
                st.caption(f"{ui.money(p.price_aed)} · {rating}")
                st.link_button("Open on Amazon", p.product_url, width="stretch")
    if len(view) > 12:
        st.caption("Cards show the first 12 matches. Use the Table tab for all.")