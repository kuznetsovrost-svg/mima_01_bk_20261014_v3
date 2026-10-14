---
name: apply-checklist-edits
description: "Use when the user provides a checklist of items to change (e.g. [ ДА]/[НЕТ] markers, numbered work-items, approval/rejection lists) and asks the model to apply them to a skill, document, or code change. Apply ONLY the marked-yes items exactly as specified; treat marked-no items as hard scope boundaries."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [workflow, editing, checklists, scope-discipline, user-instruction-following]
    related_skills: [hermes-agent-skill-authoring]
---

# Apply Checklist Edits

Discipline for applying user-supplied checklists to a target document / skill / file. The rule: **the checklist IS the spec; do not add, remove, or reorder beyond it.**

## When to Use

- User gave a bulleted or numbered list where each item is marked "yes / no / do / don't" (e.g. `[ ДА] W1 — rename`, `[НЕТ] S6 — не делать`).
- User pasted a code-review / doc-review with explicit approvals.
- User enumerated specific edits to make and explicitly closed the list.

**Don't use for:** open-ended "improve this skill" requests with no per-item scope — those invite the model to use judgment.

## Core Discipline

### 1. Parse the checklist into three buckets

- **Apply (explicit YES):** `[ ДА]`, `[Да]`, `[x]`, `[+]`, `YES`, `✓`, `DO`, marked in any way that means "change this".
- **Skip (explicit NO):** `[НЕТ]`, `[НЕ]`, `[НЕ ДЕЛАТЬ]`, `[ ]` left unchecked, `[x] DO NOT`, `NO`, `✗`, `SKIP`, marked in any way that means "leave alone".
- **Unmarked:** treat as `NO` by default. **Ask, do not assume.**

Variations in spacing/punctuation inside brackets (`[ ДА]`, `[Да ]`, `[ДА]`) are all YES — match on the word, not the formatting.

### 2. Apply ONLY the YES items, exactly

For each YES item:
- Apply the change **as the user described it** — do not reinterpret or "improve".
- Do NOT silently fix adjacent items the user did not mark, even if they look like cruft: typos, abbreviations like `#SPA`, odd headings, deprecated markup. Cost of "I cleaned up one extra thing" = user has to re-spec the change. Cost of "I didn't touch it" = zero.
- If a YES item conflicts with another YES item, stop and ask.
- If a YES item is ambiguous or technically impossible, ask before guessing.

### 3. Track progress explicitly

Before making changes, restate the checklist to the user with a count: "Applying 7 YES items, skipping 2 NO items." After, report: "Done: 7/7. Untouched per spec: 2 (item IDs: S6, W4)."

### 4. Verify before reporting done

For each YES item:
- Did the change land in the file?
- Does the change match the user's wording (not a paraphrase that "means the same thing")?
- Did any unintended side-effect appear (e.g. removing a neighbouring line that should have stayed)?

## Common Pitfalls

1. **Cleaning up adjacent cruft.** The most common failure. User marked `[НЕТ] S6 — don't change` on an item that looks like a typo. Model "fixes" it anyway as a freebie. **Don't.** Marked-NO is a hard boundary.

2. **Reformatting YES items into "improved" versions.** User wrote "rename W1". Model renamed W1, W2, W3 because they looked similar. **Don't.** Apply literally.

3. **Treating unmarked items as YES.** User left item blank or didn't mention it. Model assumes "they probably want this fixed". **Don't.** Default is NO.

4. **Adding a YES item the user didn't ask for.** Model has a "good idea" while applying changes and slips in an extra edit. **Don't.** Save it for the next turn / ask first.

5. **Losing the "skip" count.** Reporting "all done" without confirming that skipped items were not touched. User can't tell whether the model respected the boundary.

6. **Misparsing bracket variations.** `[ ДА]` (with space), `[Да]` (mixed case), `[ДА]` (all caps) all mean YES. Match on the word, not exact formatting.

## Verification Checklist

- [ ] Parsed all checklist items into YES / NO / UNMARKED buckets before editing.
- [ ] Confirmed YES count matches user's intent ("Applying N items").
- [ ] Each YES change applied **exactly** as user described (no paraphrase, no "improvement").
- [ ] Each NO item's content is byte-identical to before (verify with grep or diff if item count > 3).
- [ ] No new edits slipped in beyond the YES list.
- [ ] Final report states: "Done: X/Y. Untouched per spec: Z (item IDs: …)."

## Example Session Pattern

```
User: Apply these to foo.md:
  [ ДА] W1 — rename
  [Да ] W2 — rewrite description
  [Да] W5 — fix tags
  [НЕТ] S6 — don't touch
  [НЕТ] S5 — leave as is

Agent:
  Applying 3 YES items (W1, W2, W5), skipping 2 NO items (S6, S5).
  [patches W1, W2, W5]
  Done: 3/3. Untouched per spec: 2 (S6, S5).
  Verifying: grep S6 S5 → identical to before. ✓
```