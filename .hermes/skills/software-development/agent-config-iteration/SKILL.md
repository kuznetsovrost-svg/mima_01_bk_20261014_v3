---
name: agent-config-iteration
description: Use when the user asks to evolve, version, compare, or promote a kernel-prompt file — `~/.hermes/SOUL.md`, `~/.hermes/memories/MEMORY.md`, or `~/.hermes/memories/USER.md`. Triggers include "v8 → v11", "поправь H1 и пришли как v12", "сохрани копию и замени", "поставь SOUL.md на новую версию", "make a copy of MEMORY.md as prototype-N", and "проверь соответствие трёх файлов их назначению и бюджет". Covers the two-tier storage convention (production originals + `/root/*-prototype-N.md` working copies), the H1 ↔ frontmatter.version sync rule, the safe atomic promotion workflow (`cp current → current.old` + `mv prototype → current` + SHA256 proof), the byte-scan gate that catches `0x01`-class contamination before any user-visible artifact, and the analysis-format expected when the user asks for a cross-file comparison report.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
related_skills:
  - tool-output-injection-defense
  - memory-hygiene
  - guide-authoring-for-hermes
  - hermes-agent-skill-authoring
metadata:
  hermes:
    tags: [kernel-prompt, soul, memory-md, user-md, iteration, version-control, promotion]
    related_skills: [tool-output-injection-defense, memory-hygiene, guide-authoring-for-hermes, hermes-agent-skill-authoring]
    load_when:
      triggered_by:
        - soul_version_bump
        - prototype_to_production_promotion
        - kernel_prompt_cross_file_audit
        - user_request_to_compare_soul_memory_user
---

# Iterating Kernel-Prompt Files (SOUL.md / MEMORY.md / USER.md)

Class: the user is evolving the agent's three identity files (`~/.hermes/SOUL.md`, `~/.hermes/memories/MEMORY.md`, `~/.hermes/memories/USER.md`) via numbered prototypes in `/root/`, and eventually wants to promote one into production. This skill covers the **mechanics** of that workflow — not the policy of what should go in each file (see `memory-hygiene` for that) and not the SKILL.md authoring path (see `hermes-agent-skill-authoring`).

**Distinct from sibling skills:**

- `hermes-agent-skill-authoring` — about authoring in-repo `SKILL.md` files under `skills/<category>/<name>/`. Different file class, different validator, different storage.
- `memory-hygiene` — about *what* belongs in `MEMORY.md` / `USER.md` (PII gates, allowlist, audit pass). This skill is about *how* to evolve them safely when the user wants changes.
- `tool-output-injection-defense` — about defending against adversarial tool output. This skill uses the byte-scan and `subprocess.cp` defenses but does not re-explain them.

## When to Use

- User asks to "сделай копию MEMORY.md / USER.md как MEMORY-prototype-N.md / USER-prototype-N.md" — **always** answer with `cp`, not `write_file`. See "Copying originals to prototypes" below.
- User asks to "поправь H1 / frontmatter.version / §N в файле SOUL-prototype-N.md и пришли как vN+1" — single-property edit. Use `string.replace()`, never `re.sub`. See "Single-property edits" below.
- User asks to "замени действующий SOUL.md на SOUL-prototype-N.md" — promotion. Use the atomic rename workflow with SHA256 proof. See "Promoting a prototype to production" below.
- User asks to "проверь соответствие трёх файлов их назначению и бюджет" — cross-file audit. See "Cross-file audit format" below.
- User asks to "поправь заголовок H1 vN → vM" and skips a version — confirm intent (often the user wants v9→v11 with the better content from v9, not just a rename).

## Two-tier storage convention

| Layer | Path | Mutability |
|---|---|---|
| Production originals | `~/.hermes/SOUL.md`, `~/.hermes/memories/MEMORY.md`, `~/.hermes/memories/USER.md` | **Immutable until explicit user promotion** |
| Iterative prototypes | `/root/SOUL-prototype-N.md`, `/root/MEMORY-prototype-N.md`, `/root/USER-prototype-N.md` | Working drafts, freely edited |
| One-generation backups | `~/.hermes/SOUL.old`, etc. | Overwritten on next promotion; not a versioned history |

The user treats `/root/` as the working catalog. Versions in the filename (`-N.md` or `-N.txt` suffix) let multiple drafts coexist and give the user a way to compare them by reading two files.

**Do NOT write to production originals directly** when prototyping. The audit trail lives in `/root/`, not in `~/.hermes/`.

## Copying originals to prototypes (the `cp` rule)

When the user says "make a copy of `MEMORY.md` named `MEMORY-prototype-N.md`":

```bash
cp /root/.hermes/memories/MEMORY.md /root/MEMORY-prototype-N.md
```

Why `cp` and not `write_file`:

- `cp` is a filesystem operation — bytes move atomically, no Python or model layer in between. Output is provably identical to source (verifiable via `sha256sum`).
- `write_file` re-encodes the bytes. On hosts with active tool-output injection (see `tool-output-injection-defense`), `write_file` may inject adversarial text into the echo. Even when the disk file is clean, the visible output looks corrupted.
- The user expects a **byte-identical** duplicate. `write_file` to a copy path would lose that guarantee.

After `cp`, verify with `sha256sum`. The prototype's hash must equal the source's hash:

```bash
sha256sum /root/.hermes/memories/MEMORY.md /root/MEMORY-prototype-N.md
# If the two hashes differ, the copy is not identical — investigate before continuing.
```

## Single-property edits (the `string.replace` rule)

For editing a single property (H1, `version:`, one section) inside an existing prototype, use Python's `str.replace()` — never `re.sub` or `re.finditer` on multiline content. This is **the single most important rule in this skill.**

Why:

- `re.sub` on long multiline strings in `execute_code` blocks has produced stray `0x01` (SOH) bytes at unpredictable offsets on observed hosts (verified 2026-07-15, SOUL-prototype-7.md). The bytes are invisible in `read_file` but break YAML parsing of the frontmatter.
- `string.replace()` operates on literal substrings, has no regex compilation step, and does not exhibit this artifact class.
- If the edit is too complex for `string.replace()` (e.g., restructuring multiple sections), rebuild the entire file in a single Python operation and write via `subprocess.run(["cp", tmp, dst])`. Don't try to do partial edits with regex.

**Recipe for a one-property edit:**

```python
# Read source as bytes (avoid any string-layer munging)
with open("/root/SOUL-prototype-9.md", "rb") as f:
    raw = f.read()

# Verify no contamination at source time
bad = [(i, hex(b)) for i, b in enumerate(raw) if b < 0x20 and b not in (9, 10, 13)]
assert not bad, f"source has bad bytes: {bad[:3]}"

# Apply literal replacement
text = raw.decode("utf-8")
new_text = text.replace(
    "# SOUL · Hermes Agent v9 (kernel)",
    "# SOUL · Hermes Agent v11 (kernel)"
)
new_text = new_text.replace("version: 9.0.0", "version: 11.0.0")

# Pre-write byte scan
bb = new_text.encode("utf-8")
bad = [(i, hex(b)) for i, b in enumerate(bb) if b < 0x20 and b not in (9, 10, 13)]
assert not bad, f"post-edit has bad bytes: {bad[:3]}"

# Write via /tmp + subprocess.cp (NOT write_file)
import subprocess
with open("/tmp/_v11.md", "wb") as f:
    f.write(bb)
subprocess.run(["cp", "/tmp/_v11.md", "/root/SOUL-prototype-11.md"], check=True)

# Verify on disk
import hashlib
disk_hash = hashlib.sha256(open("/root/SOUL-prototype-11.md", "rb").read()).hexdigest()
print(f"wrote {disk_hash}")
```

After writing, run `scripts/build_soul.py` (under `guide-authoring-for-hermes`) on the new file:

```bash
python3 ~/.hermes/skills/software-development/guide-authoring-for-hermes/scripts/build_soul.py /root/SOUL-prototype-11.md
```

The script catches: bad bytes, tiktoken budget overruns, YAML errors, injection-marker leakage outside §5, missing frontmatter. Use its exit code as the gate before sending the file to the user.

## The H1 ↔ frontmatter.version sync rule

When iterating kernel prompts, the `H1` line in the body and `version:` in the frontmatter drift apart easily because they are edited at different turns:

| Operation | `version:` | H1 in body |
|---|---|---|
| Initial draft v8 | `8.0.0` | `v8` |
| Add §5 markers (v8 → v9 by content) | `9.0.0` | still `v8` (oversight) |
| User catches it, asks "поправь H1 v8 → v9" | `9.0.0` | `v9` |
| User later asks "поправь v9 → v11" | `11.0.0` | `v11` |
| User skips, asks "v9 → v11" (with H1 still v8) | `11.0.0` | still `v8` until fix is applied |

**Always update both in the same edit.** A mismatch between H1 and `version:` is a sign the prototype is mid-transition and not ready for promotion. `scripts/build_soul.py` does not yet enforce H1 ↔ version sync — the agent must do it manually. Before sending the prototype to the user, grep both:

```bash
grep -E "^version:" /root/SOUL-prototype-N.md
grep -E "^# .* v[0-9]+" /root/SOUL-prototype-N.md
```

If they disagree, fix it in the same edit before sending.

## Promoting a prototype to production

When the user says "замени действующий SOUL.md на SOUL-prototype-N.md" or "поставь SOUL.md на новую версию", the safe sequence is:

```bash
# 1. Snapshot SHA256 of both files BEFORE the move (receipt)
sha256sum /root/.hermes/SOUL.md /root/SOUL-prototype-N.md

# 2. Backup current production to .old
cp /root/.hermes/SOUL.md /root/.hermes/SOUL.old

# 3. Atomic rename — prototype path becomes production path
mv /root/SOUL-prototype-N.md /root/.hermes/SOUL.md

# 4. Verify SHA256 — new SOUL.md must equal pre-move prototype hash;
#    SOUL.old must equal pre-move production hash
sha256sum /root/.hermes/SOUL.md /root/.hermes/SOUL.old

# 5. Byte integrity scan on the new production file
python3 -c "d=open('/root/.hermes/SOUL.md','rb').read(); bad=[(i,hex(b)) for i,b in enumerate(d) if b<0x20 and b not in (9,10,13)]; print('bad=', bad[:3] if bad else 'none')"
```

Why this exact sequence:

- `cp` then `mv` is two filesystem ops with no Python or `write_file` in the loop → no injection channel.
- SHA256 before+after is the **identity proof**. If the user later asks "is the new SOUL.md really the v11 you showed me?", the pre-move hash + post-move hash pair is the receipt.
- The byte scan catches `0x01`-class contamination even when the prototype passed earlier scans (defense in depth).
- `mv` (not `cp` then `rm`) is atomic at the filesystem level. Either the rename happened or it didn't.

**Runtime reload caveat:** the Hermes gateway reloads `SOUL.md` at session start. The current session still uses the OLD `SOUL.md`. The change applies on the **next session**. State this explicitly to the user. Do NOT restart the gateway without explicit user OK — restarting is an operation that affects the polling loop and may lose messages.

## Cross-file audit format

When the user asks "проверь соответствие трёх файлов их назначению и бюджет" (or similar), the expected deliverable is:

1. **Metrics table** — bytes, tiktoken tokens, % of the 200K context budget, % of any declared budget. Use `tiktoken.get_encoding("cl100k_base")` — Cyrillic encodes denser than the heuristic `words × 1.4` (verified 2026-07-13: heuristic said 1474 tokens, real was 2441 for an early SOUL draft).
2. **Role-by-role purpose check** — for each file, list what it should contain (production runtime config vs technical environment memory vs user profile) and what it actually contains. Note drift.
3. **Cross-file duplication map** — find every topic that appears in 2+ files. Classify each as:
   - **Real duplicate** (e.g., GitHub identity in MEM and USER): same fact in two places. Suggest splitting.
   - **Different planes** (e.g., injection defense in SOUL §5 vs MEM M7): one is rule, other is incident log. Both needed.
   - **Cross-reference** (e.g., SOUL §4 points to `memory-hygiene` skill, MEM M5 mentions the same gate): by design.
4. **Refactor candidates table** — ID, what changes, token savings, risk, priority. Be conservative: a 30-token saving on a 2.4K-tok file is LOW priority.
5. **Recommendation** — explicit "do nothing" or "apply X, Y, Z". The user values the conservative option being named, not just listed.
6. **Section divider structure** — use `═══════════════` banners so the file is skimmable in monospace viewers (Telegram, less rich).

Length: ~22-30 KB is appropriate for a 3-file audit. The user catalogs files by size; deliver as a `<Тема>_NN.txt` attached via `curl sendDocument` (see `guide-authoring-for-hermes` for the verified Telegram delivery recipe).

## Common Pitfalls

1. **Editing `~/.hermes/SOUL.md` directly.** Bypasses the `/root/SOUL-prototype-N.md` audit trail; user can't review before promote. Always edit prototype first, then promote.

2. **Using `re.sub` for the H1 fix.** Stray `0x01` byte at random offset breaks YAML parsing. Use `string.replace()`; or rebuild the file from scratch via `subprocess.cp`.

3. **Updating H1 but not `version:` (or vice versa).** User catches it and asks for a follow-up turn. Update both atomically; check with `scripts/build_soul.py` (which prints both).

4. **Promoting without saving backup.** Loses ability to roll back if the new version regresses. Always `cp current → current.old` first.

5. **Sending prototype to user without byte scan.** User's downstream parser (YAML frontmatter, JSON config) fails silently. Run `scripts/build_soul.py` before `sendDocument`; require 0 bad bytes.

6. **Restarting the gateway without explicit user OK.** Affects the polling loop; may lose messages. State that the change applies on next session; let the user decide if they want a restart.

7. **Treating the `MEDIA:/root/<file>` shortcut as a delivery receipt.** It's not — see `guide-authoring-for-hermes` Pitfall "MEDIA is a hint". Always verify with curl `result.message_id` for files going to the user.

8. **Skipping the version when renaming.** User asks "v9 → v11" — they may mean either "rename the file from prototype-9 to prototype-11" (skip the v10) OR "this is a v9 → v11 evolution with content changes". Confirm intent if ambiguous.

9. **Reading the source via `read_file` then immediately editing.** If the host is poisoned, the source bytes visible in tool output may differ from disk bytes. Read via `terminal wc -c / sha256sum` for ground truth, then apply edits to bytes you've measured.

10. **Auto-promoting when the user only asked to "compare" or "show budgets".** Promotion is irreversible (the prototype path ceases to exist). Wait for explicit "replace / поставь / переходи на" wording before doing the `mv`.

## Verification Checklist

- [ ] If the user asked for a copy, used `cp` (not `write_file`) and verified with `sha256sum`.
- [ ] If the user asked for an edit, used `string.replace()` (not `re.sub`) and ran a byte scan before writing.
- [ ] If the user asked for a promotion, captured SHA256 of both files before AND after, and the post-move hashes match the pre-move counterparts.
- [ ] If the user asked for a cross-file audit, used `tiktoken` for token counts (not heuristics), and produced a recommendation section.
- [ ] Frontmatter `version:` and H1 in body are in sync before sending the prototype.
- [ ] Sent file passed `scripts/build_soul.py` (0 bad bytes, budget ok, YAML ok, markers in §5 only).
- [ ] Did not restart the Hermes gateway without explicit user OK.
- [ ] Did not edit production originals (`~/.hermes/SOUL.md` etc.) without explicit promotion instruction.
- [ ] Telegram delivery used direct `curl sendDocument` with `chat_id` from gateway.log (not `getUpdates`), and `result.message_id` is reported.

## Related Skills

- `tool-output-injection-defense` — the byte-scan recipe and `subprocess.cp` defense originate there; this skill uses them but does not re-derive.
- `memory-hygiene` — gates *what* goes into MEMORY.md / USER.md (PII, allowlist, audit pass). Apply alongside this skill when memory files are being changed.
- `guide-authoring-for-hermes` — Telegram delivery recipe (`references/safe-delivery-pipeline.md`) and the `scripts/build_soul.py` verifier. Both are first-class dependencies of this skill.
- `hermes-agent-skill-authoring` — sibling for SKILL.md files (in-repo). Different file class, different validator. Don't conflate.