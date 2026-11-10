<!-- Split out of SKILL.md; the entry point keeps a one-line pointer plus the guards that fail silently. Content has been edited since the split - do not assume it still matches any older copy of SKILL.md. -->

# `entity: aiGroup` — you get the *currently effective* config, not the raw record

Two server-side transformations are applied to `aiActionSettings` / `aiAutomation` before you see them. Both remove fields. **A missing field means "not in effect right now" — it does not mean "not configured", and it never means "a write failed".**

**1. Trimmed by ad type.** The response only carries what's configurable for that `campaignType`:

| campaignType | What's absent |
|---|---|
| `sponsoredProducts` | nothing (full set); automation limited to the supported rule set |
| `sponsoredBrands` | `structOptimization`; and in `bidOptimization`: `bidAdPlaceStatus`, `bidAdPlaceRangeStatus`, `tosMin/tosMax`, `pdpMin/pdpMax`, `rosMin/rosMax`, `bidAmazonBusinessStatus`, `btbMin/btbMax`, `btbRangeStatus`; plus `targetPausedAddStatus` |
| `sponsoredDisplay` | `bidOptimization`, `structOptimization`, `brandOptimization`; in `budgetOptimization`: `budgetDaypartStatus`, `budgetDynamicStatus`, `numType`, `num`; the `negativeTarget*` family and `targetPausedAddStatus`; **all** automation rules |

If `campaignType` is missing or unrecognized, nothing is trimmed.

**2. Projected to what's actually effective.** On top of the trim:

- A switch that is **off** drops its dependent fields. `bidAdPlaceStatus=0` → no `tosMin/tosMax/pdpMin/pdpMax/rosMin/rosMax`. `btbRangeStatus=0` → no `btbMin/btbMax`. `bidRangeStatus=0` → no `bidRangeType`/`bidRange`. `brandedStatus=0` → no `brandedMatchType`/`brandedList`/`competitor*`; `competitorStatus=0` → no `competitorMatchType`/`competitorList`.
- A rule running in **AI mode** (`status=0`, or absent) is **omitted from `aiAutomation` entirely** — the system decides on its own, so there's no rule config to show.
- **Never interpret an empty `aiAutomation` by itself.** It can mean that all *enabled* rule-capable action spaces are AI-driven, that those action spaces are off, or a mixture of both. Read the paired `aiActionSettings` switches first; only an on switch with no retained Rule entry identifies AI mode for that action space.
- A rule running in **Rule mode** (`status=1`) keeps its config but drops AI-panel-only parameters (e.g. rule 181 drops `bidPerformanceStrictAcosStatus`; rule 17 drops `numType`/`num`).
- `targetPausedAddStatus=2` is reported as `1` in Rule mode (the AI-only sub-option is folded away).

**`aiAutomation.{ruleType}.status` is a mode discriminator, not an enable switch.** Never
translate `status=1` as "enabled" or `status=0` as "disabled". The paired
`aiActionSettings.*Status` switch determines whether the action space is on; when it is on,
`status=1` means Rule mode and an omitted Rule entry means AI mode.
**How to talk about this to a user:**

**Before presenting a managed-group configuration, read
[`managed-group-display.md`](managed-group-display.md).** It defines the
customer-facing language, UI grouping, setting labels, and rule names. Backend object names are
not product section names.
- Report what's present as the live configuration. For anything absent, say "not currently in effect" and, if relevant, name the switch that gates it — don't say "not set" and don't guess at a stored value.
- If the user asks "did my change save?", verify by reading the **switch** you set, then its dependents. Absent dependents under an off switch are expected, not evidence of failure.
- Don't diff two `aiGroup` reads field-by-field and call every disappearance a regression — flipping one switch off legitimately removes a whole family of fields from the response.
- If the user asks for the **full / complete managed-group configuration**, do not compress
  sibling controls into a phrase such as "bid adjustment + placement + range". Group the
  returned switches by the UI's Bid / Budget / Targeting / Structure sections and report each
  supported switch separately, including off switches. For every on, rule-capable switch, report
  AI vs Rule mode and then its dependent values. A field trimmed because the ad type does not
  support it is "unsupported / not exposed for this ad type", not "off".
- Map `targetType` through the managed-group display guide and preserve the UI's selected objective
  label in the user's language. For example, a Chinese answer for `targetType=2` says **保持订单稳定**.
  "控制成本" is only the surrounding category, and a returned English label such as "Optimize
  ROAS" must not replace the selected Chinese option.
- For managed groups and their schedules, display `aiPersonality` as the numeric level only, for
  example **AI 人格：4**. Do not replace or supplement it with `aiPersonalityText` labels such as
  "激进", "略激进", or "Aggressive".
- Treat bid-range values according to `bidRangeType`. `2` is a numeric amount in store currency
  — never call that a coefficient. **`bidRangeType=1` IS a coefficient** (`1.13` = 1.13x the
  base bid), **not a percentage**: show the raw number, never append `%`, and never convert it
  to one. Never infer that placement adjustment is on merely because bid range is on.
- Do not show backend field names or rule numbers in a normal customer answer. Use localized UI
  names from the display guide. Raw keys/codes belong only in a separate technical appendix when
  explicitly requested.
- `brandOptimization` is not an action-space category. Present it separately as Brand/non-brand/
  competitor mode / 品牌/非品牌/竞品模式.

## Reading rule-mode (RBA) rule configuration

There are two different read surfaces; do not conflate them:

- `entity: "automationRule"` returns only the enabled `ruleType` codes and localized names for specified Amazon campaign IDs. It does **not** return template IDs/names, conditions, actions, frequency, applicable objects, or account-level template lists.
- `entity: "aiGroup"` (and, when present, `aiGroup_schedule`) returns the managed group's embedded action-space Rule configuration under `aiAutomation.{ruleType}`. This is not the account's standalone automation-template library.

When a managed group runs an action space in **Rule mode**, its effective configuration is readable under `aiAutomation.{ruleType}`: conditions, actions, condition items, time periods, and (for dayparting rules) the hour matrix. Rule types you may see: `2` bid dayparting, `4` target harvest, `5` negative target, `13` budget dayparting, `17` budget by performance, `19` placement adjustment, `20` pause campaign, `181` bid by performance, `182` target pause/supplement.

**Before explaining any rule configuration, read [`automation-rule-reading.md`](automation-rule-reading.md).** It defines the action-switch/mode decision, capability boundary, rule-specific business semantics, condition priority, and safe rendering procedure.

- Well-understood leaves carry a `...Text` companion for display (metric names, logical connectors, action types, placements, periods, hour labels). Leaves whose value domain isn't confirmed are passed through **raw, with no Text** — relay those verbatim and don't invent a label for them.
- The same raw value can mean different things in different rules (e.g. `amount` under rule 17 is a budget action, under rule 19 it's a placement bid action). Never carry a label across rule types.
- **This is read-only.** There is no MCP tool that writes RBA rule configuration — see `sparkx-edit-ai-group`. You can show a user their rule setup and explain it; you cannot offer to change it here. Also note the direction constraint: a rule-based group can be switched to AI, but not the reverse.

## Current controller inventory for one campaign

When the user asks "what can still change this campaign's bid/budget?", "what remains on after
I disabled one control?", or requests the full current control setup, do not answer from one
row or one field. Build a **current-state controller inventory** in this order:

1. Resolve the campaign with `entity: campaign`; keep both internal `campaignId` and
   `amazonCampaignId`, plus `aiGroupId`, current `dailyBudget`, bidding strategy and status.
2. If `aiGroupId > 0`, read that `entity: aiGroup` row. Inventory every supported switch in
   `aiActionSettings` by the UI sections defined in `managed-group-display.md`. For each enabled,
   rule-capable switch, use `aiAutomation` to state **AI mode** or **Rule mode** and render the
   current effective limits/configuration.
3. Query `entity: aiGroup_schedule` for the group. Report active/current and future schedules
   separately; a schedule is a possible override, not proof that it caused a past change.
4. Query `entity: automationRule` with the campaign's **Amazon** id to list enabled standalone
   campaign automation types. This surface is only an enabled-type summary; do not invent its
   hidden conditions, actions or next execution time.
5. Report any budget-management or other mechanism only when the returned campaign/group fields
   actually establish it. Missing data is "not exposed in this read", not proof that no controller
   exists.

Present a compact customer-facing inventory under Bid controls, Budget controls, Targeting,
Structure, Schedules and Standalone automation. Use UI labels, never backend keys or `Rule N`.
State what disabling one switch does **not** disable: for example, turning off bid-by-performance
does not by itself turn off bid dayparting or placement adjustment when those switches remain on.

This inventory is current configuration only. It can answer what may continue acting now; it
cannot prove which controller caused a historical adjustment. Pair it with `get_operation_log`
for that question.

## Budget and limit wording

Do not collapse distinct returned values into "budget cap" or "maximum":

- campaign `dailyBudget` is the campaign's configured daily budget;
- managed-group `totalBudget` / `totalDailyBudget` are sums across campaigns, with the meanings
  stated by their returned labels;
- a Rule action bound is a rule-specific floor/ceiling;
- a logged `currentBudget` or other transient value is a point-in-time operational value.

Name the source field in a technical appendix when needed, but use its customer-facing label in
the answer. Only call a value an upper/lower limit when the returned configuration explicitly
defines it as one. Never infer that a transient value plus a configured daily budget reveals the
algorithm that produced it.
