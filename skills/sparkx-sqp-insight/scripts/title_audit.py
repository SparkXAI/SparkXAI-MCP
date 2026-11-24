#!/usr/bin/env python3
"""
title_audit.py - check product titles against the searches shoppers actually use (help-center
use case "Audit your title and copy against real search behavior").

Inputs:
  --sqp     own-ASIN x search rows, loaded through sqp_rows.py: get_market_search_perf JSON with
            factEntity marketAsinQuery, or the ASIN detail export (.xlsx, one sheet per ASIN).
  --titles  JSON list of {"asin", "parentAsin", "asinTitle"} (or "title") from
            get_entity_metadata(entity='asin'); a whole tool response is fine too.
Output: JSON per ASIN with its top searches by volume and, for each, whether the title holds the
phrase as typed, holds all its words in another order, or misses words. Deterministic, stdlib only.

Usage: python title_audit.py --sqp rows.json --titles titles.json [--top 15] [--out audit.json]
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqp_rows  # noqa: E402  (the only module that names SQP columns)

STOP = {"for", "and", "with", "the", "of", "a", "an", "in", "to", "by", "&"}


def norm(t):
    t = str(t or "").lower()
    t = re.sub(r"[^a-z0-9+ ]", " ", t)
    return " ".join(t.split())


def stem(w):
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def words(t):
    return [stem(w) for w in norm(t).split() if w not in STOP]


def load_sqp(paths):
    """Own-ASIN x search window rows (weeks added): {asin: [{query, volume, purch, impr}]}."""
    rows, _ = sqp_rows.load(paths)
    win = sqp_rows.collapse_weeks([r for r in rows if r["asin"] and r["source_kind"] in sqp_rows.ASIN_KINDS])
    by = {}
    for r in win:
        by.setdefault(r["asin"], []).append({"query": r["query"], "volume": r["search_volume"],
                                             "purch": r["purch_brand"], "impr": r["impr_brand"]})
    return by


def check(title, query):
    nt, nq = " " + norm(title) + " ", norm(query)
    if f" {nq} " in nt:
        return "phrase"
    tw, qw = set(words(title)), words(query)
    missing = [w for w in qw if w not in tw]
    if not missing:
        return "words_other_order"
    return "missing:" + " ".join(missing)


def audit(by_asin, titles, top=15):
    out, no_title = [], []
    for asin, g in sorted(by_asin.items()):
        t = titles.get(asin)
        if not t:
            no_title.append(asin)
            continue
        g = sorted(g, key=lambda x: -(x["volume"] or 0))[:top]
        rows = [{"query": r["query"], "volume": r["volume"], "brand_purchases": r["purch"],
                 "in_title": check(t, r["query"])} for r in g]
        # Word-order finding: a bigger search that only matches by words, while a smaller
        # variant matches as a phrase (e.g. "oil of oregano" vs "oregano oil").
        order = []
        phr = [x for x in rows if x["in_title"] == "phrase"]
        for x in rows:
            if x["in_title"] == "words_other_order":
                for y in phr:
                    if set(words(y["query"])) == set(words(x["query"])) and (x["volume"] or 0) > (y["volume"] or 0):
                        order.append({"bigger_search": x["query"], "volume": x["volume"],
                                      "title_uses": y["query"], "volume_title_phrase": y["volume"]})
        missing = [x for x in rows if x["in_title"].startswith("missing")]
        out.append({"asin": asin, "title": t, "top_searches": rows,
                    "phrase_coverage_top": sum(x["in_title"] == "phrase" for x in rows) / len(rows) if rows else None,
                    "missing_count": len(missing), "word_order_findings": order,
                    "missing_volume": sum((x["volume"] or 0) for x in missing)})
    out.sort(key=lambda x: -x["missing_volume"])
    return out, no_title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqp", nargs="+", required=True)
    ap.add_argument("--titles", required=True)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--out", default="title_audit.json")
    a = ap.parse_args()
    with open(a.titles, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta = meta.get("data", {}).get("rows", meta) if isinstance(meta, dict) else meta
    titles = {}
    for r in meta:
        t = r.get("asinTitle") or r.get("title")
        for k in (r.get("asin"), r.get("parentAsin")):
            if k and t and k not in titles:
                titles[k] = t
    out, no_title = audit(load_sqp(a.sqp), titles, a.top)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"asins": out, "asins_without_title": no_title,
                   "note": "'phrase' = title contains the search as typed; 'words_other_order' = all words present, "
                           "different order (Amazon indexes these separately for ranking); 'missing:' lists words absent "
                           "from the title. Check bullets and backend search terms before changing the title."},
                  fh, indent=1, default=str, ensure_ascii=False)
    print(a.out, len(out), "asins;", len(no_title), "without title")


if __name__ == "__main__":
    main()
