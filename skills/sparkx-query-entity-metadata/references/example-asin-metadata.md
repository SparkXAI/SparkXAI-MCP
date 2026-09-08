# ASIN Metadata Query (with Parent ASIN + Product Line)

```json
{
  "profileIds": [4404871489220462],
  "entity": "asin",
  "filters": {"asinBrand": {"like": "%Samsung%"}},
  "orderBy": [{"field": "asinPrice", "direction": "DESC"}],
  "pageSize": 10,
  "userContext": "Samsung-brand ASINs"
}
```

Each returned row nests parent-ASIN fields (`parentAsinTitle`, `parentAsinBrand`, etc.) and a `productLines` array alongside the child-ASIN fields — no separate call needed to get parent/product-line info.

**Multi-profile note**: if `profileIds` has more than one entry, each row carries its own `currency` field and amounts are **not** converted to USD. `asin` was the first entity to work this way; **all AdsList entities now follow the same rule** (e.g. `{"asin": "B0XX", "asinPrice": 29.99, "currency": "USD"}`). Check that field per-row rather than assuming a shared currency.
