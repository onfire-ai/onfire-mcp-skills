---
name: onfire-manage-ai-prospecting
description: Inspect and edit the caller's AI Prospecting schema configuration via the Onfire `manage_ai_prospecting` tool. Use when the user wants to view their prospecting schema (regions, ranking, keywords, prompts, tags), draft changes safely without touching the live config, test those changes with shadow runs, then promote or discard them. Covers the full shadow lifecycle: get_my_schema, get_shadow, create_shadow, update_shadow, ship_shadow, discard_shadow.
---

# manage_ai_prospecting (atomic)

Edits the caller's prospecting schema via a **shadow** (per-user draft copy). Iterate in chat → test with `ai_prospecting(activate_shadow_run=True, ...)` → promote when satisfied. All operations are scoped to the caller from OAuth — no tenant/email arguments.

> **Note:** earlier versions of this skill described `manage_ai_prospecting` as a read-only SQL surface. That is no longer accurate. The current tool is the shadow-schema editor described here.

## When to use this

- "What's in my prospecting schema?" / "Show me my regions / keywords / ranking config."
- "I want to tweak the prompt / hot keywords / regions and try it out without breaking my live setup."
- "Promote my draft to live."
- "Throw away the draft."

Don't use this to trigger prospecting runs — that's `ai-prospecting`. Don't use this to inspect run history (that's not in this tool's surface anymore).

## The lifecycle

```
get_my_schema → create_shadow → update_shadow (× N) → ai_prospecting(activate_shadow_run=True)
                                                         │
                                                         ├─ happy → ship_shadow(confirm=True)
                                                         └─ unhappy → discard_shadow
```

Always start with `get_my_schema` to see what's actually live before proposing edits.

## Actions

### `get_my_schema`

Returns `{live, shadow}` for the caller. The agent's source of truth before any edit.

```python
manage_ai_prospecting(action="get_my_schema")
```

### `get_shadow`

Returns the caller's current shadow row (404 if none).

```python
manage_ai_prospecting(action="get_shadow")
```

### `create_shadow`

Copies the caller's live schema into a new shadow row, named after the caller's email, with the caller as the only `team_member`.

**Shortcut:** if the caller is already solo on a schema whose `team` matches their email domain, the existing row is flipped to `is_shadow=TRUE` in place — no duplicate row. Edits made during testing remain on the live row when discarded (see "Pitfalls").

```python
manage_ai_prospecting(action="create_shadow")
```

### `update_shadow`

Apply a `patch` dict of editable fields. Protected columns (`id`, `tenant`, `team`, `team_members`, `is_shadow`, `created_at`, `updated_at`) are rejected server-side.

```python
manage_ai_prospecting(action="update_shadow", patch={
    "included_regions": ["NA", "EMEA"],
    "hot_keywords": ["platform engineering", "observability"],
    "cold_keywords": ["intern", "student"],
    "ranking_config": {...},
    "prospect_match_prompt": "...",
    "relevancy_filter_prompt": "...",
    "client_technologies": [...],
    "prompt_modules": [...],
    "prospect_tags_schema": [...],
    "exclusion_keywords": [...],
    "authority_score_threshold": 0.6
})
```

Editable fields include (non-exhaustive):
- `included_regions`
- `prospect_match_prompt`
- `relevancy_filter_prompt`
- `ranking_config`
- `hot_keywords`
- `cold_keywords`
- `exclusion_keywords`
- `client_technologies`
- `prompt_modules`
- `prospect_tags_schema`
- `authority_score_threshold`

If the user asks to edit a field that the server rejects, surface the error rather than retrying — it's likely protected on purpose.

### Test the draft

Not part of this tool — call `ai_prospecting`:

```python
ai_prospecting(action="run", activate_shadow_run=True, company_linkedin_url="...")
```

A 404 from this means there is no shadow yet — call `create_shadow` first.

### `ship_shadow`

Promotes shadow → live. **Requires `confirm=True`.** Removes the caller from any other live schema so the "one live schema per user" invariant holds. The caller's previous base schema keeps its remaining members.

```python
manage_ai_prospecting(action="ship_shadow", confirm=True)
```

Confirm with the user before flipping `confirm=True`. This is the destructive step.

### `discard_shadow`

Deletes the shadow row. For shortcut rows (where `create_shadow` flipped the live row in place), `is_shadow` is flipped back to `NULL` — but **any edits made during testing remain on the live row**. This is a documented caveat of the shortcut path; warn the user before discarding if they used the shortcut.

```python
manage_ai_prospecting(action="discard_shadow")
```

## Hard rules

- **Always `get_my_schema` before proposing edits.** Don't edit blind.
- **Confirm before `ship_shadow(confirm=True)`.** It's the only destructive action and the irreversible one.
- **Warn before `discard_shadow` on a shortcut row.** Edits leak onto live; the user may not realize.
- **No tenant/email args.** Identity comes from OAuth. Anything you pass will be ignored or rejected.
- **Don't assume protected columns are editable.** If `update_shadow` rejects a field, it's protected — surface the error, don't retry.

## Common pitfalls

- **Calling `update_shadow` before `create_shadow`.** Returns 404. Create the shadow first.
- **Forgetting `confirm=True` on `ship_shadow`.** It will refuse.
- **Confusing shadow with live.** After edits, `get_my_schema` returns both — be explicit which one you're showing the user.
- **Shortcut surprise on discard.** When `create_shadow` used the in-place shortcut, `discard_shadow` doesn't fully roll back — edits stay on live. Tell the user before they pull the trigger.
- **Calling this tool to "see last week's runs".** That history surface isn't here anymore. If the user wants run history, tell them this tool no longer exposes it.

## Worked examples

**Tweak hot keywords and test.**
```
1. manage_ai_prospecting(action="get_my_schema") — show user current keywords.
2. manage_ai_prospecting(action="create_shadow") — if no shadow exists yet.
3. manage_ai_prospecting(action="update_shadow", patch={"hot_keywords": [...new list...]})
4. ai_prospecting(action="run", activate_shadow_run=True, company_linkedin_url="...")
5. Show prospects, ask if they like the change.
6. ship_shadow(confirm=True)  OR  discard_shadow.
```

**Just looking.**
```
manage_ai_prospecting(action="get_my_schema") — render live config; no edits.
```

**Abort a draft.**
```
1. get_my_schema — confirm a shadow exists, check whether it's a shortcut row.
2. If shortcut: warn user that edits remain on live.
3. discard_shadow.
```

## What this skill does NOT do

- It doesn't run prospecting — that's `ai-prospecting` (with `activate_shadow_run=True` to test).
- It doesn't expose run history or arbitrary SQL. Those interfaces no longer exist on this tool.
- It doesn't manage tenant-level config across users — only the caller's own schema.
