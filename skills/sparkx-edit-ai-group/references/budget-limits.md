# Budget limits (site- and account-type-specific)

Budget min/max are enforced by the platform UI (e.g. the total-budget field shows
"预算至少 $1，最多 $1000000"). **MCP bypasses this.** But these limits vary by **site**
and by **account type (seller vs vendor)**, and:

- the authorized context does **not** reliably tell you whether a profile is seller or
  vendor, and
- the exact per-site ranges are **only partly known / still being confirmed** with the
  backend.

So this skill **cannot fully validate a budget on its own** - don't hard-block a value
against a table you can't complete. Handle it this way instead:

1. **Prefer the backend.** Send the budget and let the backend validate; if it returns
   a range error, relay it to the user clearly (site, and the allowed range if given).
2. **Sanity-check only what you can determine reliably.** A few rules are safe to apply
   up front when you know the site:
   - **JP is integer-only** - never send a decimal budget for a JP-site group.
   - Budget must be **positive** and within any range you *do* know for that exact
     site/type.
   - **Multi-campaign minimum scales with campaign count** (effective min ~ per-campaign
     min x campaign count) - if the user's total looks too low for the number of
     campaigns, flag it.
3. **Don't invent limits.** If you're not sure of a site's range or the account type,
   don't fabricate a number or silently clamp - say you can't fully verify it and let
   the backend be the gate.

## Known anchors (informational - confirm before hard-relying)

- US SP: min ~1, max ~1,000,000. US **SD vendor** max is much lower (~50,000).
- JP: min ~100, max ~21,000,000, integer-only.
- IN: SP min ~50; SB seller min ~100; vendor min ~500.

> **Open item:** whether the backend enforces these ranges is being confirmed with the
> product/backend team. If it does, this skill just relays errors. If it doesn't
> (front-end-only), a queryable "budget limits by site/account" source is needed so the
> skill can validate reliably - until then, treat the numbers above as guidance, not a
> hard gate.
