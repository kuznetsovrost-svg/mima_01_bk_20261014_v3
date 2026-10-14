# Hermes Profile Architecture — verified 2026-08-09

> Session-anchored reference. Real paths, PIDs, file lists, and code
> excerpts from the 2026-08-09 session that diagnosed the
> `default`-profile-missing issue, classified the four-tier skill
> visibility model, and identified the bundled-skill catalogue. Keep this
> short; link to source files where the truth lives.

---

## 1. State of `/root/.hermes/profiles/` on `mima_g_01`

```
default/                   NOT EXISTS (created during session, see §6)
analyst_training/          23 entries in skills/
fst-control/               25 entries in skills/
mi_mg_01/                  28 entries in skills/
```

The `default/` directory did not exist before this session. The implicit
"default" gateway (PID 33769) was using `/root/.hermes/.env` for tokens
and a bare `hermes_cli.main gateway run` invocation.

## 2. Gateway → profile → bot mapping

| PID | Command | Profile | Token file | Bot |
|---|---|---|---|---|
| 33769 | `hermes_cli.main gateway run` (no `--profile`) | implicit `default` | `/root/.hermes/.env` | `@MMRV_Hermes_bot` (id 8933960684) |
| 40198 | `hermes_cli.main --profile analyst_training gateway run` | `analyst_training` | `/root/.hermes/profiles/analyst_training/.env` | `@HM_analyst_training_bot` (id 8733809491) |
| 78290 | `hermes_cli.main --profile fst-control gateway run` | `fst-control` | `/root/.hermes/profiles/fst-control/.env` | `@fst_control_bot` (id 8934212474) |

The bot → profile mapping is **by token file**, not by directory layout.
Cross-profile token confusion is the most common routing pitfall.

## 3. Code-grounded pointers

### `SKILLS_DIR` definition

`/usr/local/lib/hermes-agent/tools/skills_tool.py`:

```python
HERMES_HOME = get_hermes_home()
SKILLS_DIR = HERMES_HOME / "skills"   # = /root/.hermes/skills (global user)
```

`all_dirs = [SKILLS_DIR] + get_external_skills_dirs()` — global user is
unconditional, bundled and profile skills arrive via external dirs.

### `seed_profile_skills` opt-out

`/usr/local/lib/hermes-agent/hermes_cli/profiles.py`:

```python
NO_BUNDLED_SKILLS_MARKER = ".no-bundled-skills"

def has_bundled_skills_opt_out(profile_dir: Path) -> bool:
    return (profile_dir / NO_BUNDLED_SKILLS_MARKER).exists()

# Inside seed_profile_skills:
if has_bundled_skills_opt_out(profile_dir):
    return {"copied": [], "updated": [], "user_modified": [],
            "skipped_opt_out": True}
```

The marker is the on-disk signal that `--no-skills` set. Web dashboard
sync and `hermes update` honour it too.

### Collision detection

`/usr/local/lib/hermes-agent/tools/skills_tool.py`:

```python
# Collision detection: collect ALL candidates across every dir using
# every lookup strategy (direct path, recursive by parent dir name,
# legacy flat <name>.md). If more than one matches, refuse and tell
# the caller — silent shadowing of a local skill by a same-named
```

Always probe `[ -e "$dest" ]` before `cp -r` bundled → global.

## 4. Bundled skill catalogue (68 skills across 18 categories)

Verified by walking `/usr/local/lib/hermes-agent/skills/` on 2026-08-09.
Total size ~7.3 MB. The 33-skill subset recommended for cross-profile
promotion is in the parent SKILL.md ("Copying bundled skills to global").

| Category | Count | Notable skills |
|---|---|---|
| `apple/` | 4 | apple-notes, apple-reminders, findmy, imessage (macOS only) |
| `autonomous-ai-agents/` | 4 | claude-code, codex, hermes-agent, opencode |
| `computer-use/` | 0 | (empty) |
| `creative/` | 16 | excalidraw, architecture-diagram, comfyui (364K), popular-web-designs (964K) |
| `data-science/` | 1 | jupyter-live-kernel |
| `dogfood/` | 2 | references, templates (Hermes internal) |
| `email/` | 1 | himalaya |
| `github/` | 6 | github-pr-workflow, github-code-review, github-auth |
| `index-cache/` | 0 | (empty) |
| `media/` | 4 | youtube-content, gif-search, heartmula, songsee |
| `mlops/` | 4 | evaluation, inference, models, huggingface-hub |
| `note-taking/` | 1 | obsidian |
| `productivity/` | 9 | powerpoint (1.2M), google-workspace, maps, notion, airtable |
| `research/` | 5 | research-paper-writing (1.5M), arxiv, llm-wiki, polymarket |
| `smart-home/` | 1 | openhue |
| `social-media/` | 1 | xurl |
| `software-development/` | 9 | plan, test-driven-development, systematic-debugging, simplify-code |
| `yuanbao/` | 0 | (empty) |

## 5. Global user skills (already in `/root/.hermes/skills/`)

32 entries on 2026-08-09, including the cross-cutting essentials
(`memory-hygiene`, `failsafe-rules`, `officecli`, `figma-api-import`,
`excalidraw`) and the rest of the bundled set already promoted by the
user. When promoting bundled → global, the conflict-safe recipe in the
parent SKILL.md is mandatory because 28 of the 33 recommended skills
are *already* in `/root/.hermes/skills/` (verified via `[ -e ... ]`).

## 6. The `default/` profile bootstrap recipe

What was done to create `/root/.hermes/profiles/default/` from scratch
during this session:

```bash
SRC=/root/.hermes/profiles/analyst_training
DST=/root/.hermes/profiles/default

mkdir -p "$DST"/{skills,memory,cron,sessions,logs,cache,workspace,
                audio_cache,image_cache,hooks,plans,projects}
cp "$SRC/SOUL.md"   "$DST/SOUL.md"
cp "$SRC/config.yaml" "$DST/config.yaml"
```

What was **not** done:
- No new gateway was started (the existing PID 33769 keeps running).
- No `.env` was created — `default` continues to use
  `/root/.hermes/.env`.
- No bundled skills were seeded (default `skills/` stays empty until
  the user decides between copying or `--no-skills`-ing).

## 7. Verify-this-list before trusting it

The above figures are anchored to:
- `ps auxf | grep hermes` (2026-08-09)
- `ls /root/.hermes/profiles/*/skills/` (2026-08-09)
- `ls /usr/local/lib/hermes-agent/skills/` (2026-08-09)
- `grep -A 5 "SKILLS_DIR\s*=" tools/skills_tool.py` (Hermes 2026-08)

Re-run these commands in any new session before citing numbers — the
directory layout changes as profiles are added, and Hermes itself
upgrades bundled content between releases.