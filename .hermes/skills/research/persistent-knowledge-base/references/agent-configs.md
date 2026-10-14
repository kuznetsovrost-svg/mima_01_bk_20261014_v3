# Agent Configuration Templates — Multi-Vault

YAML configs for `/root/wiki-system/agents/<profile>.yaml`. Each profile in your Hermes install gets its own YAML.

## When to use

- Every Hermes profile that will touch the wiki needs a YAML here
- The skill reads `$HERMES_PROFILE` to find which YAML applies
- If a profile tries to write to a vault not in its `allowed_vaults`, the skill refuses with a clear error

## Template — main agent (`default.yaml`)

The default agent (Rost) gets access to every domain:

```yaml
agent: default
description: "Main agent (Rost) — every domain"
allowed_vaults:
  - engineering
  - research
  - hermes-platform
  - product-strategy
  - personal-growth
default_vault: engineering
permissions:
  read: all
  write: all
restricted_paths:
  - vaults/_archive/
created: 2026-08-25
```

## Template — restricted research agent (`analyst_training.yaml`)

A specialized profile that only sees research + system context:

```yaml
agent: analyst_training
description: "Analyst training agent — research + system context only"
allowed_vaults:
  - research
  - hermes-platform
default_vault: research
permissions:
  read: allowed
  write: allowed
restricted_paths:
  - vaults/personal-growth/
  - vaults/_archive/
created: 2026-08-25
```

## Template — automation agent (`fst-control.yaml`)

A profile for cron jobs and automated workflows:

```yaml
agent: fst-control
description: "Automation agent — engineering + system only"
allowed_vaults:
  - engineering
  - hermes-platform
default_vault: engineering
permissions:
  read: allowed
  write: allowed
restricted_paths:
  - vaults/personal-growth/
  - vaults/_archive/
created: 2026-08-25
```

## Template — read-only agent (`viewer.yaml`)

A profile that can query but cannot ingest:

```yaml
agent: viewer
description: "Read-only viewer — can query, cannot modify"
allowed_vaults:
  - engineering
  - research
  - product-strategy
default_vault: engineering
permissions:
  read: all
  write: none         # ← key difference
restricted_paths:
  - vaults/_archive/
created: 2026-08-25
```

## Field reference

| Field | Required | Purpose |
|---|---|---|
| `agent` | yes | Profile name (matches `$HERMES_PROFILE`) |
| `description` | yes | Human-readable summary |
| `allowed_vaults` | yes | Which vaults this profile can touch |
| `default_vault` | yes | Fallback when no `--vault` flag passed |
| `permissions.read` | yes | `all` (everything), `allowed` (only in allowed_vaults), `none` |
| `permissions.write` | yes | Same scale as read |
| `restricted_paths` | no | Extra paths blocked even within allowed vaults (e.g. `_archive/`) |
| `created` | yes | ISO date — for audit |
| `notes` | no | Free text — rationale, caveats |

## Resolution order at runtime

When the skill starts:

1. Read `$HERMES_PROFILE` → profile name
2. Load `/root/wiki-system/agents/<profile>.yaml`
3. If file missing → fail loudly: "Unknown agent profile"
4. When user runs a command with `--vault X`:
   - If `X` in allowed_vaults → proceed
   - Else → refuse with allowed_vaults list
   - If `X` in restricted_paths → refuse even if it's in allowed_vaults
5. When no `--vault` flag → use `default_vault`

## Adding a new profile

1. Create `/root/wiki-system/agents/<new_profile>.yaml` from one of the templates
2. Customize allowed_vaults
3. Test: in a session with `HERMES_PROFILE=<new_profile>`, run `vault-curator.py show-config`
4. Expected output: agent name + allowed_vaults + default_vault

## Pitfalls

- **`write: all` is dangerous** — only the human's main profile (`default`) should have this. Restricted profiles get `write: allowed` at most
- **`_archive/` should be in restricted_paths** for all profiles including default — never auto-modify archived vaults
- **Don't reuse the same default_vault for every profile** — each profile's default should match its primary working vault
- **Adding a profile without `created`** — audit becomes impossible; always include it