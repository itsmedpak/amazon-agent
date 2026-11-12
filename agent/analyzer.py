def analyze_trends(current_products, previous_products):
    previous = {
        product["asin"]: product
        for product in previous_products
        if product["asin"]
    }

    results = []

    for product in current_products:
        item = dict(product)
        old = previous.get(product["asin"])

        if old:
            previous_rank = old["rank"]
            item["rank_change"] = previous_rank - product["rank"]

            if item["rank_change"] > 0:
                item["trend"] = "Improved"
            elif item["rank_change"] < 0:
                item["trend"] = "Declined"
            else:
                item["trend"] = "Unchanged"
        else:
            item["rank_change"] = None
            item["trend"] = "New entry" if previous else "Baseline"

        results.append(item)

    return results