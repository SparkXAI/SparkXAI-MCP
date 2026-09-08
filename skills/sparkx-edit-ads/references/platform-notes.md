# Platform notes - read this first

Covers the one tool, its scope, the response envelope, every error you can observe, and
how to tell a failure from an unknown outcome.

## The tool

`batch_update_ads(entity, action, request, userContext)` - a write tool: non-idempotent and
destructive by declaration.

| Parameter | Type | Notes |
|---|---|---|
| `entity` | string | same vocabulary as `get_entity_metadata`'s entity |
| `action` | string | only registered `entity`+`action` pairs execute |
| `request` | object | route-specific payload; **must** contain `profileIds` |
| `userContext` | string | the user's own request plus why, **max 100 characters** |

`userContext` is not decoration - it lands in the audit log. Write what the user actually
asked for, not a restatement of the API call. Over 100 characters is rejected.

`tenantId` and `userId` are injected server-side from the token and **cannot** be passed or
overridden. The operator recorded against the change comes from the same place. Do not try
to supply a `username`.

## Scope

This tool requires **`amazon_sa_campaign_edit:write`**, which is separate from the managed
group scopes. It is a newer scope, so tokens issued before it existed will not carry it.

**On `scope_missing` or `permission_denied`: stop.** It means this token is not authorized
for ad editing. Tell the user they need to re-authorize with the ad-editing permission.
**Do not retry, do not try a different route, and do not attempt to achieve the same change
through another tool.** A permission the user has not granted is not an obstacle to route
around.

## profileIds is all-or-nothing

This tool **rejects the whole batch** if `request.profileIds` contains anything unauthorized
(`Unauthorized profileIds: [...]`). It never silently narrows the scope. **The read tools
behave the same way** - `get_entity_metadata` raises `Requested profileIds contain
unauthorized values` rather than intersecting - so there is no "reads are lenient, writes are
strict" asymmetry to remember.

Every item's own `profileId` is checked too - it must appear in `request.profileIds`, or the
batch is rejected.

Consequence: never pad `profileIds` "to be safe". Send exactly the profiles the write needs.

## Response envelope

```json
{ "isError": false,
  "toolName": "batch_update_ads",
  "data": { },
  "meta": { "effectiveProfileIds": [4404871489220462], "hint": "..." },
  "requestId": "..." }
```

- Check `isError` first, then read the top-level **`errorType`**. All pipeline and
  validation failures use `errorType`.
- `meta.hint` sometimes carries information available nowhere else - read it.
- **`requestId` is the support handle. Quote it whenever you report a failed write to the
  user.**

## Internal-route results are three-state

The five internal routes (`campaign` budget/status, `negativeKeyword` create, `keyword`
create, `target` create) return:

```json
{ "total": 3, "successCount": 2, "failCount": 1,
  "results": [ { "id": 1001, "success": true },
               { "id": 1002, "success": false, "message": "..." } ] }
```

`isError: false` with `failCount > 0` is a **partial success**. Derive the succeeded set
from `results[]`, report exactly which items failed, and **never present a partial result as
full success**. Retry only the failed ids, and only after confirming with the user if the
scope changed.

Page routes return `{code, message, data}` on success only - a downstream business failure
is raised as a tool error, so **checking `data.code` for failure never finds one.**

## `ambiguous_write` - the one you must not retry

Raised when the downstream call returned 200 but the result did not line up (empty results,
a count that does not match what was submitted, a null entry, a missing `success` flag, or
an id that is not one you sent), or when the call timed out or returned a non-2xx.

**It means the state is unknown, not that nothing happened.** The write may well have
applied.

1. Do **not** retry.
2. Read the affected entities back with `get_entity_metadata`.
3. Tell the user what you found and let them decide.

This matters most where a blind retry changes state twice - budget and bid deltas above all.

**Idempotency of `create` varies by route**, so do not generalise:

- `keyword + create` and `negativeKeyword + create` **de-duplicate downstream** - an entry
  that already exists in the target ad group / campaign is skipped rather than duplicated.
- `target + create`, `productAd + create`, `negativeTarget + create` / `copy` and
  `negativeKeyword + copy` have **no documented de-duplication** - assume a retry duplicates.

Either way, on an unknown outcome the rule is the same: **read the entities back first, never
retry blindly.**

## Errors you can actually observe

| `errorType` | Meaning / what to do |
|---|---|
| `invalid_params` | Field, enum, or batch-composition problem - **also** an archived-guard rejection (archived / unknown state / unresolvable id). Read the message before assuming it is malformed JSON. A guard *lookup failure* is `business_error`, not this |
| `business_error` | Downstream or query-execution failure, **and all confirmation-token errors**. Read the message and branch: unknown field -> fix it; result set too large -> narrow; execution timeout -> narrow and retry; server is busy -> retry later; internal error -> likely transient |
| `ambiguous_write` | State unknown - verify, do not retry (above) |
| `write_operation_failed` | The downstream write was rejected |
| `timeout` | Narrow the batch and retry, **after** reading the entities back |
| `rate_limited` | Wait `retryAfterSeconds`; do not retry immediately |
| `scope_missing` / `permission_denied` | Not authorized - stop and tell the user (above) |
| `token_invalid` / `api_not_authorized` | Auth problem - the user must re-authenticate |
| `profile_out_of_range` | A profileId is outside the authorized set |
| `service_unavailable` / `auth_service_unavailable` / `rate_limit_service_unavailable` | Infrastructure - report and stop; do not hammer |

Messages from `business_error` are wrapped by the service layer
(`Service [Amazon_SA_Service] returned an error: ...`); `invalid_params` messages are not.
**Branch on `errorType`; if you must inspect text, substring-match, never exact-match.**

## Rate limits

The configured write budget is **20 calls/min**, per tenant+tool and per user+tool (reads
get 120). Whether limiting is enabled is an environment setting, so treat it as a ceiling to
plan against rather than something you can count on being off.

A confirmation flow costs **two** calls, and a write/read-back loop adds a read each time. A
serial pass over many entities will hit the ceiling - batch instead of looping, and honour
`retryAfterSeconds` on `rate_limited`.

## Verify - the envelope is not proof

After any write, re-read the entities with `get_entity_metadata` and confirm the fields took
the values you intended. This is mandatory for anything irreversible, anything bid- or
budget-related, and anything that returned `ambiguous_write` or `timeout`.

When reconciling a budget change, remember that the confirmation preview's `currentBudget`
is the campaign's **`dailyBudget`** - see [`confirmation.md`](confirmation.md).
