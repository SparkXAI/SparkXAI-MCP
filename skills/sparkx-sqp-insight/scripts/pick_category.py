#!/usr/bin/env python3
"""pick_category.py - plan mode Step 1 default when the user names no category.

Default = the BSR category of the parent ASIN with the most ad spend in the current window.
Reference = the fastest-growing parent ASINs (total sales vs the previous window, minimum size)
outside that category, and up to N other categories, offered as "also worth a look".

Inputs: two get_ads_perf pulls (factEntity=asin, select asin.parent_asin_, metrics Spend, Sales,
ACOS, TotalSalesAmount) for the current and previous 4 weeks, and the parent -> category map
(a JSON object, or get_entity_metadata entity=asin rows with parentAsin and
parentAsinBsrCategoryName / asinBsrCategoryName). Stdlib only; reads no SQP data.
"""
import argparse, json


def rows_of(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return d.get("data", {}).get("rows", d.get("rows", [])) if isinstance(d, dict) else d


def key(r):
    for k in ("parent_asin", "asin.parent_asin_", "parent_asin_", "parentAsin"):
        if r.get(k):
            return r[k]
    return None


def cat_map(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d, dict) and "data" not in d and "rows" not in d:
        return d
    out = {}
    for r in rows_of(path):
        p = r.get("parentAsin") or r.get("asin")
        c = r.get("parentAsinBsrCategoryName") or r.get("asinBsrCategoryName")
        if p and c:
            out.setdefault(p, c)
    return out


def pick(cur, prev, cmap, min_sales_share=0.005, n=3):
    tot = sum(r.get("TotalSalesAmount") or 0 for r in cur.values())
    top = max(cur.values(), key=lambda r: r.get("Spend") or 0)
    default_cat = cmap.get(key(top))
    growth = []
    for p, r in cur.items():
        t = r.get("TotalSalesAmount") or 0
        pv = (prev.get(p) or {}).get("TotalSalesAmount")
        if not pv or t < min_sales_share * tot:
            continue  # new products (no previous) are listed separately, not ranked
        growth.append({"parent_asin": p, "category": cmap.get(p), "total_sales": round(t),
                       "growth_pct": round((t / pv - 1) * 100, 1), "spend": round(r.get("Spend") or 0),
                       "acos": r.get("ACOS"),
                       "acos_up_more_than_3pt": (r.get("ACOS") or 0) > (prev[p].get("ACOS") or 0) + 3})
    growth.sort(key=lambda x: -x["growth_pct"])
    ref_cats = []
    for g in growth:
        if g["category"] and g["category"] != default_cat and g["category"] not in ref_cats:
            ref_cats.append(g["category"])
        if len(ref_cats) == n:
            break
    new = [{"parent_asin": p, "category": cmap.get(p), "total_sales": round(r.get("TotalSalesAmount") or 0)}
           for p, r in cur.items() if p not in prev and (r.get("TotalSalesAmount") or 0) >= min_sales_share * tot]
    return {"default_category": default_cat,
            "top_spend_asin": {"parent_asin": key(top), "spend": round(top.get("Spend") or 0), "acos": top.get("ACOS")},
            "reference_growth_asins": [g for g in growth if g["category"] != default_cat][:n],
            "reference_categories": ref_cats, "new_products": new[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", required=True)
    ap.add_argument("--previous", required=True)
    ap.add_argument("--category-map", required=True)
    ap.add_argument("--min-sales-share", type=float, default=0.005)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--event-in-previous", default="", help="an event inside the previous window, shown as a caveat")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cur = {key(r): r for r in rows_of(a.current) if key(r)}
    prev = {key(r): r for r in rows_of(a.previous) if key(r)}
    out = pick(cur, prev, cat_map(a.category_map), a.min_sales_share, a.n)
    if a.event_in_previous:
        out["notes"] = [f"the previous window includes {a.event_in_previous}; growth is understated for products that sold heavily in it"]
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
