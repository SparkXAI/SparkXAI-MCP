---
name: sparkx-manage-keyword-list
description: >-
  Create, read, edit and delete keyword lists (corpus) - reusable sets of plain keyword texts
  that AI managed groups and campaigns reference by id instead of repeating the words. Covers
  get_keyword_list, create_keyword_list, update_keyword_list and delete_keyword_list: list
  metadata and keywords, add or remove keywords, link or unlink products, change visibility
  (private / public read / public collaborative), and delete with two-phase confirmation. Use
  when the user wants to build, inspect, extend, trim, share or remove a keyword list, asks
  which lists exist, or asks what is in one. Keyword lists carry no match type and no brand
  flag - those are chosen where the list is used, so applying a list to a campaign or ad group
  belongs to sparkx-create-campaign, and applying one to a managed group's branded / competitor
  / harvest-exclusion settings belongs to sparkx-edit-ai-group. Not for negative keywords on a
  live campaign (use sparkx-edit-ads).
metadata:
  version: 1.0.0
---

# Manage Keyword Lists

A keyword list is a named bag of keyword texts bound to one or more shops. It carries **no
match type and no brand flag** - those are decided at the place the list is referenced. The
same list can be a branded list on one managed group and a harvest-exclusion list on another.

Four tools, all behind the `amazon_sa_keywords_list:write` scope - **including the read one**.
A user without that scope sees none of them, so "I cannot find the keyword list tools" usually
means the token lacks the scope, not that the feature is off.

| Tool | Does |
|---|---|
| `get_keyword_list` | List mode (search + metadata + counts) or detail mode (one list, optionally with products / linked AI groups / keywords) |
| `create_keyword_list` | New list with name, shops, visibility, optional initial keywords and products |
| `update_keyword_list` | One `target` per call: `keywords`, `products` or `visibility` |
| `delete_keyword_list` | 1-20 lists, **always two-phase** |

Call `get_user_authorized_context` first. **One unauthorized profile id rejects the whole
request** on every tool here.

## Read first, almost always

Nothing in this skill takes keyword text as an identifier - everything takes `keywordListId`.
So unless the user handed you an id, start with `get_keyword_list` in list mode and let them
pick. Two filters make that cheap: `nameContains` (with `nameExact`) and `containsKeyword`
(with `containsKeywordExact`) - the latter answers "which list has this word in it".

**List mode does not return keywords**, only metadata and counts. To see words, call detail
mode with `include: ['keywords']`; `page` / `pageSize` then page the *keywords*, and list-only
filters are ignored. `include` also takes `products` (first 100, `meta.truncated` says whether
more exist) and `linkedAiGroups` (which groups use the list, with usage flags).

**Rule-based (auto-updating) lists are invisible here**: excluded from list mode, rejected in
detail mode, rejected by every write. If a user insists a list exists and you cannot find it,
say it may be rule-based and has to be managed in the platform - do not tell them it is gone.

`otherProfileCount` is the number of bound shops outside the profiles you passed. A non-zero
value means the list reaches further than what you are showing - say so before the user edits
or deletes it.

## Creating

Required: `name` and 1-50 shops. Everything else is optional.

- **Name**: 1-100 characters after trimming; no control characters, no invisible formatting
  characters (a zero-width space is rejected, not stripped - a name pasted from a doc can fail
  for something you cannot see), no 4-byte characters such as emoji. Must be unique **among
  the lists you created**, not globally.
- **Visibility** defaults to `PRIVATE`. The other values are `PUBLIC_READ` and
  `PUBLIC_COLLABORATIVE`.
- **Keywords** (optional, at most 1000 per call): trimmed, blanks dropped, duplicates removed
  case-insensitively. **Any single keyword over 80 characters rejects the whole call** - check
  lengths before sending a pasted batch. The literal keywords `null` and `-1` are dropped and
  reported in `warnings`.
- **Products** (optional, at most 50 distinct `{profileId, product}`): the product dimension is
  `asin` (default), `parentAsin` or `sku`, fixed at creation and **not changeable afterwards**.
  Pick it deliberately.

Creation **executes immediately - there is no confirmation step**, so show the user the name,
shops and keyword count before you call it, not after.

Renaming a list and changing its shops are **not available** yet. If the user wants either,
say so rather than offering a delete-and-recreate - that loses the links to any managed group
or campaign using it.

## Updating: one target per call

`target` is `keywords`, `products` or `visibility`, and **fields belonging to another target
are rejected** rather than ignored. The id count differs per target - this is the easiest thing
to get wrong:

| `target` | `action` | `keywordListIds` | Other |
|---|---|---|---|
| `keywords` | `add` / `remove` required | **1-10** | `keywords`, at most 1000 |
| `products` | `add` / `remove` required | **exactly 1** | 1-50 distinct `{profileId, product}` |
| `visibility` | **omit** | **1-20** | `visibility` |

What each one does to things already in the list:

- **keywords / add**: existing keywords are skipped. Matching is **case-sensitive downstream**,
  so `Shoe` is added even when `shoe` is already there - warn the user before bulk-adding
  capitalised variants. A list that would exceed its keyword limit fails while the others
  continue.
- **keywords / remove**: exact, case-sensitive match; anything not present comes back as
  `notFound`, not as an error.
- **products / add**: `asin` and `parentAsin` lists require 10-character ASINs (uppercase
  letters and digits). Products already linked are skipped. Products the recommendation service
  silently refuses (no ASIN authorization) come back as `dropped` - **report those, they did
  not get linked**.
- **products / remove**: missing ones are `notFound`; ones still linked afterwards are
  `notRemoved` - also report these, the removal did not take.
- **visibility**: lists already at the target value come back `changed=false`. **A list used by
  an AI group cannot be set to `PRIVATE`**, and only the creator or an admin can change
  visibility at all.

Every profile id you pass for `products` must be a shop of that list **and** authorized for
you, or the whole call is rejected.

`status` is `success` or `partial_success` for keywords and visibility. **Only when every list
fails does the call return an error** - so a successful envelope with per-list failures inside
is normal. Read `results[]` per list and report the failures; never summarise a
`partial_success` as done.

## Deleting

`delete_keyword_list` takes 1-20 ids and **always requires two phases**: call without
`confirmToken` to get a preview, show the preview to the user, wait for an explicit yes, then
repeat the same call with the returned `confirmToken`.

**Deleted lists cannot be restored.** Lists in use by an AI group are rejected downstream -
unlink them in `sparkx-edit-ai-group` first. Results come back per list as `DELETED` or
`REJECTED`; a mixed result is normal and must be reported list by list.

Before previewing a delete, read the list with `include: ['linkedAiGroups']` and tell the user
what will break. `otherProfileCount > 0` means shops outside your view are affected too.

## Where lists get used

This skill manages the lists. **Pointing something at a list lives elsewhere**, and the match
type is chosen there, not here:

| Use | Where | Field |
|---|---|---|
| Keywords / negatives on a new campaign or ad group | `sparkx-create-campaign` | `keywordLists` / `negativeKeywordLists` on the ad group item |
| Branded / competitor mode on a managed group | `sparkx-edit-ai-group` | `brandedList` / `competitorList` plus their `MatchType` |
| Harvest and negative-target exclusions on a managed group | `sparkx-edit-ai-group` | `targetHarvestBlackList` / `negativeTargetBlackList` plus their `MatchType` |
| Keywords on a live campaign from a list | `sparkx-edit-ads` | `fromKeywordList` |

A referenced list is **1-10 ids** everywhere. Whether it **replaces** or **adds** depends on
the place: a managed group's lists are replaced and stay linked; a campaign or ad group expands
or copies the words in **once** and adds them to what is already there. Never tell a user their
existing keywords will be overwritten by a campaign-side reference. Details in
[`references/using-lists.md`](references/using-lists.md).

## Before you write

1. **Resolve the list by id, from a read.** Never act on a name the user typed without
   confirming which id it maps to - names are unique only per creator.
2. **Say what else uses it.** `linkedAiGroups` and `otherProfileCount` before any edit or
   delete.
3. **Show the shape of the change**: which list, add or remove, how many keywords or products,
   and for visibility what it is going from and to.
4. **Read the per-list results back** and report `notFound` / `dropped` / `notRemoved` /
   `REJECTED` explicitly. A partial success is not a success.
