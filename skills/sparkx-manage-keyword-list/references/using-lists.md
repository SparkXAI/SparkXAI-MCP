# Referencing a keyword list from somewhere else

This skill creates and edits the lists. Every place that *uses* one lives in another skill.
What they share: the reference is **ids, never words**, and the id comes from
`get_keyword_list`.

## One rule holds everywhere, one does not

**1-10 ids per field, duplicates removed** - that one is universal.

**Whether the reference replaces or adds depends on where you use it.** Getting this backwards
is the expensive mistake, so check which column you are in:

| Where | Semantics |
|---|---|
| AI managed group (`brandedList`, `competitorList`, `targetHarvestBlackList`, `negativeTargetBlackList`) | **Replaces** the current value. The group keeps a live reference to the lists. Read what is there first and resend the ids you want to keep |
| New campaign / ad group (`keywordLists`, `negativeKeywordLists`) | **Expands once into real keywords** at creation. Nothing is replaced |
| Live campaign (`createFromKeywordList`) | **Copies the words in once, adding to what is already there.** Existing keywords are not touched and nothing is removed |

So "I am pointing this campaign at my brand list" never wipes its current keywords, while the
same sentence about a managed group does replace the group's list.

## Where each one lives

### New campaign or ad group - `sparkx-create-campaign`

`create_sp_sb_campaign`, `create_sp_ad_group` and `create_sb_ad_group` take two optional
objects on each ad group item. The server expands them into real keywords before writing, so
what lands on Amazon is ordinary keywords, not a live link to the list - **later edits to the
list do not flow through to campaigns built this way**. Say that when a user expects the
campaign to follow the list.

| Field | Expands to | Shape |
|---|---|---|
| `keywordLists` | keyword targeting | `keywordListIds` (1-10), `matchTypes` (`exact` / `phrase` / `broad`, case-sensitive), `bid` (required, > 0, at most 2 decimals), `state` (`enabled` default, or `paused`) |
| `negativeKeywordLists` | ad-group-level negative keywords | `keywordListIds` (1-10), `matchTypes` (`negativeExact` / `negativePhrase`) |

- `matchTypes` is a list: one expanded keyword per match type per word. Two match types over a
  200-word list is 400 keywords. Two caps apply to the whole request, not per ad group: **at
  most 10 distinct keyword lists per call**, and **5,000 total child items after expansion**.
  Estimate before sending; both errors tell you to split the request.
- `bid` is **required** on `keywordLists` and applies to every expanded keyword. There is no
  per-word bid here; if the user wants different bids, expand the words yourself and pass
  `keywords` instead.
- Normal ad group rules still apply after expansion: keyword targeting needs a `keyword` ad
  group, and an SP auto ad group cannot take keywords.
- If the server has keyword-list features disabled, passing either object is **rejected** with
  a message telling you to pass keywords explicitly - it does not silently ignore them.
- Expanding to nothing (every word filtered out) is an error, not an empty success.

### AI managed group - `sparkx-edit-ai-group` / `sparkx-create-ai-group`

Here the reference **stays live** - the group keeps pointing at the list. Six fields in two
nodes, all taking `keywordListId`:

| Node | Switch | List | Match type |
|---|---|---|---|
| `brandOptimization` | `brandedStatus` | `brandedList` | `brandedMatchType` |
| `brandOptimization` | `competitorStatus` | `competitorList` | `competitorMatchType` |
| `targetOptimization` | `targetHarvestBlackListStatus` | `targetHarvestBlackList` | `targetHarvestMatchType` |
| `targetOptimization` | `negativeTargetBlackListStatus` | `negativeTargetBlackList` | `negativeTargetMatchType` |

- **A switch set to `1` requires its `MatchType` in the same request** (`1` = exact, `2` =
  phrase), otherwise the call fails with
  `aiActionSettings.<x>MatchType is required when <x>Status=1`.
- **`competitorStatus=1` requires `brandedStatus=1`.**
- `[]` empties a list and needs the matching switch turned off in the same request.
- The list must be non-rule-based and bound to that `profileId`.
- The UI labels these match types **equals / contains**, while targeting and harvest screens
  label the same `1` / `2` **exact / phrase**. Same codes, different wording per screen - use
  the wording of the screen the user is looking at.

### Live campaign - `sparkx-edit-ads`

`batch_update_ads` accepts a `fromKeywordList` source for keyword writes. Same id-based
reference, same one-shot expansion as campaign creation.

## Checking the other direction

`get_keyword_list` in detail mode with `include: ['linkedAiGroups']` answers "what uses this
list". It covers **AI managed groups only** - campaigns built by expansion have no link back,
because they got copies of the words.

So "is this list safe to delete" has two halves: `linkedAiGroups` tells you about groups, and
nothing tells you about campaigns. Say that rather than implying the check was complete.
