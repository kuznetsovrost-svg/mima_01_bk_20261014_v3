# AGENTS.md Schema — Per-Vault Wiki Schema

A standard `AGENTS.md` template for individual wiki vaults in a multi-vault setup. Copy this into each vault and customize the placeholders.

## When to use

- Each vault in a multi-vault system has its own `AGENTS.md` describing how the agent should behave in that specific vault
- This is the per-vault equivalent of the global `SCHEMA.md` (single-wiki) — but smaller, vault-specific, and rooted in Karpathy's pattern of "schema = the discipline file"
- The agent reads this at the start of every session for that vault (orientation step)

## Template

Save as `<vault>/AGENTS.md`. Replace `{{...}}` placeholders.

```markdown
## Purpose

This wiki is a structured, interlinked knowledge base for {{vault_name}} vault.
Claude/Hermes maintains the wiki. The human curates sources, asks questions, and guides the analysis.


## Folder structure

\`\`\`
00_Inbox/        -- new materials before processing
10_Sources/      -- source documents (immutable -- never modify these)
20_Notes/        -- human notes and diary
80_Wiki/         -- markdown pages maintained by LLM
  index.md       -- table of contents for the entire vault
  log.md         -- append-only record of all operations
  sources/       -- source summary pages
  entities/      -- entity pages (people, organizations, products)
  concepts/      -- concept pages (theories, methods)
  comparisons/   -- comparison pages
  synthesis/     -- synthesis pages
90_Synthesis/    -- LLM-generated analytical pages
\`\`\`


## Ingest workflow

When the user adds a new source to `10_Sources/` and asks you to ingest it:

1. Read the full source document
2. Discuss key takeaways with the user before writing anything
3. Create a summary page in `80_Wiki/sources/` named after the source
4. Create or update concept/entity pages for each major idea or entity
5. Add wiki-links ([[page-name]] or [[othervault:page-name]]) to connect related pages
6. Update `80_Wiki/index.md` with new pages and one-line descriptions
7. Append an entry to `80_Wiki/log.md` with the date, source name, and what changed

A single source may touch 10-15 wiki pages. That is normal.

Show the plan to the user before writing anything.


## Page format

Every wiki page should follow this structure:

\`\`\`markdown
# Page Title

**Summary**: One to two sentences describing this page.

**Sources**: List of source files this page draws from.

**Last updated**: Date of most recent update.

---

Main content goes here. Use clear headings and short paragraphs.

Link to related concepts using [[wiki-links]] throughout the text.

## Related pages

- [[related-concept-1]]
- [[related-concept-2]]
\`\`\`


## Citation rules

- Every factual claim should reference its source file
- Use the format (source: filename.pdf) after the claim
- If two sources disagree, note the contradiction explicitly
- If a claim has no source, mark it as needing verification


## Question answering

When the user asks a question:

1. Read `80_Wiki/index.md` first to find relevant pages
2. Read those pages and synthesize an answer
3. Cite specific wiki pages in your response
4. **If the answer is not in the wiki, say so clearly**
5. If the answer is valuable, offer to save it as a new wiki page

Good answers should be filed back into the wiki so they compound over time.


## Lint

When the user asks you to lint or audit the vault:
- Check for contradictions between pages
- Find orphan pages (no inbound links from other pages)
- Identify concepts mentioned in pages that lack their own page
- Flag claims that may be outdated based on newer sources
- Check that all pages follow the page format above
- Report findings as a numbered list with suggested fixes


## Rules

- Never modify anything in the `10_Sources/` folder
- Always update `80_Wiki/index.md` and `80_Wiki/log.md` after changes
- Keep page names lowercase with hyphens (e.g. `machine-learning.md`)
- Write in clear, plain language
- **When uncertain about how to categorize something, ask the user**
- Never modify a page with `reviewed: true` in frontmatter without explicit confirmation
- Cascade limit: max 3 levels of updates per single ingest

## Cross-vault references

When mentioning an entity from another vault, use the format: [[othervault:Page Name]].

Other vaults in this wiki-system:
{{list_of_other_vaults}}

## Vault-specific notes

(Specific rules for this vault: priority tags, ignored sources, reviewed pages, etc.)
```

## Differences vs single-wiki `SCHEMA.md`

| Aspect | Single-wiki `SCHEMA.md` | Multi-vault `AGENTS.md` (this template) |
|---|---|---|
| Scope | Whole `~/wiki` directory | One vault at a time |
| Where it lives | `~/wiki/SCHEMA.md` (or similar) | `<vault_root>/AGENTS.md` |
| Scope of conventions | Global tag taxonomy, global rules | Vault-specific tags, vault-specific rules |
| Cross-vault links | N/A | `[[othervault:Page Name]]` format |
| Layout convention | User-defined | 5-6 fixed sections (entities/concepts/sources/comparisons/synthesis) |

## Pitfalls

- **Don't duplicate the global SCHEMA.md rules** — if a rule is global, it belongs in a parent config, not in every vault's AGENTS.md
- **Don't put secrets or large references in AGENTS.md** — it's read every session; keep it small
- **Keep the vault-specific notes section empty by default** — populate only when you have learned something that applies only to this vault
- **AGENTS.md is consulted before any other orientation step** — if it's wrong or outdated, every session inherits the mistake