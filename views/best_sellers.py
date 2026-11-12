import streamlit as st

import ui

category = st.session_state["category"]
data = ui.require_data(category)
df, has_prev = data["df"], data["prev_run"] is not None

f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
query = f1.text_input("Search product", placeholder="e.g. sofa, desk, shelf")
min_rating = f2.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)
only_priced = f3.checkbox("Only products with a price", value=False)
statuses = []
if has_prev:
    statuses = f4.multiselect("Movement", sorted(df["status"].unique()))

view = df.copy()
if query:
    view = view[view["title"].str.contains(query, case=False, na=False)]
if min_rating > 0:
    view = view[view["rating"] >= min_rating]  # unrated products are excluded
if only_priced:
    view = view[view["price_aed"].notna()]
if statuses:
    view = view[view["status"].isin(statuses)]
view = view.sort_values("rank")

st.caption(f"Showing {len(view)} of {len(df)} products.")

table_tab, cards_tab = st.tabs(["Table", "Cards"])

with table_tab:
    cols = ["image_url", "rank", "title", "price_aed", "rating", "reviews"]
    if has_prev:
        cols += ["rank_change", "status"]
    cols += ["product_url"]
    st.dataframe(
        view[cols], hide_index=True, width="stretch", height=640,
        column_config={
            "image_url": st.column_config.ImageColumn("Image"),
            "rank": st.column_config.NumberColumn("Rank", format="%d"),
            "title": st.column_config.TextColumn("Product", width="large"),
            "price_aed": st.column_config.NumberColumn("Price (AED)", format="%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%.1f"),
            "reviews": st.column_config.NumberColumn(
                "Ratings", format="%d", help="Number of customer ratings. Not sales."),
            "rank_change": st.column_config.NumberColumn(
                "Rank change", format="%d", help="Positive = moved up since previous snapshot"),
            "status": st.column_config.TextColumn("Movement"),
            "product_url": st.column_config.LinkColumn("Amazon", display_text="Open"),
        },
    )
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
        for col, (_, p) in zip(cols, shown.iloc[start:start + 4].iterrows()):
            with col, st.container(border=True):
                if p["image_url"]:
                    st.image(p["image_url"], width=150)
                st.markdown(f"**#{int(p['rank'])}** {p['title'][:80]}")
                st.caption(f"{ui.money(p['price_aed'])} · "
                           f"{'no rating' if p['rating'] != p['rating'] else str(p['rating']) + ' ★'}")
                st.link_button("Open on Amazon", p["product_url"])
    if len(view) > 12:
        st.caption("Cards show the first 12 matches. Use the Table tab for all.")