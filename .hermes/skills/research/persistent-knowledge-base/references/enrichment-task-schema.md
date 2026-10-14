# JSON Enrichment-Task Schema

The complete schema for JSON blocks that humans embed in stub Obsidian notes to direct the server-side agent's enrichment work. See the parent skill's "Enrichment Pipeline" section for the high-level rationale.

## When to use

- A user is building a wiki-vault by hand in local Obsidian and wants the agent to fill in bodies
- You're processing a batch of stub notes that follow this protocol
- You're writing or auditing the JSON inside a stub note

## Top-level shape

```json
{
  "enrich": { ... },             // REQUIRED — what to do with the note
  "context_from_graph": { ... }, // OPTIONAL — how to read neighbours
  "remove_after": true,          // DEFAULT true — strip the JSON after the body is written
  "replace_body": true,          // DEFAULT true — wipe everything between the H1 and this block
  "review": { ... }              // OPTIONAL — self-check criteria
}
```

## `enrich` block

| Field | Type | Required | Meaning |
|---|---|---|---|
| `type` | enum | yes | `entity` / `concept` / `synthesis` / `comparison` / `note` |
| `purpose` | string | yes | One sentence: why this note exists |
| `depth` | enum | yes | `expand` / `decompose` / `compare` / `illustrate` / `synthesize` |
| `audience` | enum | yes | `beginner` / `intermediate` / `expert` |
| `length` | enum | yes | `brief` (200-300w) / `1page` (400-600w) / `2page` (700-1000w) / `long` (1500+w) |
| `must_cover` | string[] | yes | List of points — each becomes a paragraph or section |
| `avoid` | string[] | no | What NOT to write (scope guard) |
| `must_reference_pages` | string[] | yes | Notes to `[[wikilink]]` from the new body |
| `illustrate` | object[] | no | Diagrams / tables to embed |
| `structure_hint` | string | no | Suggested H2/H3 order |

### `type` enum

| Value | When to use |
|---|---|
| `entity` | Person, organization, product, model, system |
| `concept` | Idea, pattern, method, theory |
| `synthesis` | Pulls together multiple sources/notes into a new conclusion |
| `comparison` | Side-by-side: alternatives, trade-offs |
| `note` | Reference / observation — short, mostly links |

### `depth` enum

| Value | What the agent does |
|---|---|
| `expand` | Take a one-paragraph summary and turn it into a full note |
| `decompose` | Break a complex thing into parts, explain each |
| `compare` | Compare against alternatives, surface trade-offs |
| `illustrate` | Keep the existing prose, add diagrams / tables |
| `synthesize` | Read multiple linked notes and produce a new conclusion |

### `audience` enum

| Value | Lexicon | Depth |
|---|---|---|
| `beginner` | Plain language, define jargon | High-level, no implementation details |
| `intermediate` | IT jargon OK | Moderate technical detail |
| `expert` | Full jargon, link to specs | Deep technical content |

### `length` enum

| Value | Word target |
|---|---|
| `brief` | 200-300 |
| `1page` | 400-600 |
| `2page` | 700-1000 |
| `long` | 1500+ |

`length` is a ceiling, not a goal. If the topic is exhausted at 400 words, write 400.

### `illustrate` object

```json
{
  "kind": "mermaid | table | external",
  "title": "What to call the illustration",
  "what": "What the illustration should show (one sentence)"
}
```

- `mermaid` — embed as a `\`\`\`mermaid` code block; Obsidian renders natively
- `table` — markdown table with explicit columns from `what`
- `external` — placeholder for an image URL; requires the human to drop the file

Always specify `kind`. Without it the agent may emit ASCII art that Obsidian can't render.

## `context_from_graph` block

| Field | Type | Required | Meaning |
|---|---|---|---|
| `neighbours` | string[] | no | Notes to read for context |
| `use_neighbour_content` | enum | no | `summary_only` / `summary_and_links` / `full` |

| `use_neighbour_content` | What the agent reads |
|---|---|
| `summary_only` | First paragraph + H1 of each neighbour (default; covers 80% of tasks) |
| `summary_and_links` | Above + the `[[wikilinks]]` from each neighbour |
| `full` | Full body of each neighbour (only for `synthesize` depth on small graphs) |

`neighbours` typically equals `must_reference_pages` — they can be the same list. Split them only when the task says "mention X but study Y in detail".

## `review` block

| Field | Type | Meaning |
|---|---|---|
| `audience_check` | string | "After reading, the user should understand X" — the agent self-tests against this |
| `length_target_words` | number | Numeric ceiling on output length |

## Minimal example

```json
{
  "enrich": {
    "type": "entity",
    "purpose": "Quick reference for X",
    "depth": "expand",
    "audience": "beginner",
    "length": "1page",
    "must_cover": ["What X is", "Why X exists", "How X is used"]
  },
  "remove_after": true,
  "replace_body": true
}
```

## Full example

```json
{
  "enrich": {
    "type": "concept",
    "purpose": "Explain Y so a developer can decide whether to use it",
    "depth": "decompose",
    "audience": "intermediate",
    "length": "2page",
    "must_cover": [
      "Definition of Y in 2-3 sentences",
      "Anatomy: what Y is built from",
      "Lifecycle: how Y is created, lives, retires",
      "Categories of Y with examples",
      "Best practices"
    ],
    "avoid": [
      "Deep implementation details (separate notes)",
      "History of Y",
      "Comparison with specific competitors"
    ],
    "must_reference_pages": ["Concept A", "Concept B"],
    "illustrate": [
      {"kind": "mermaid", "title": "Anatomy of Y", "what": "Component tree"},
      {"kind": "mermaid", "title": "Lifecycle of Y", "what": "State diagram from create to deprecate"}
    ],
    "structure_hint": "Definition → Anatomy (diagram) → Lifecycle (diagram) → Categories → Best practices"
  },
  "context_from_graph": {
    "neighbours": ["Concept A", "Concept B"],
    "use_neighbour_content": "summary_only"
  },
  "remove_after": true,
  "replace_body": true,
  "review": {
    "audience_check": "Reader can decide whether Y fits their use case",
    "length_target_words": 800
  }
}
```

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `must_cover: ["Tell me more about X"]` | Vague, sprawling body | One sentence per array element, each becomes a paragraph |
| No `must_reference_pages` | Note has zero `[[wikilinks]]`, breaks the graph | Always require at least 2-3 wikilinks |
| `use_neighbour_content: full` on 50-node graph | Context overflow, agent hallucinates | Default to `summary_only`; `full` only for `synthesize` on small graphs |
| `illustrate: ["add diagram"]` without `kind` | ASCII art that Obsidian won't render | Always specify `kind: mermaid` / `table` / `external` |
| `replace_body: false` with placeholder text | New body glues onto `[TODO]` text | Default to `replace_body: true` |
| Forgetting `remove_after` | JSON block survives in the final note | Default to `true` |
| Processing 50 notes in one go | No review, no schema iteration | Process 5-10, review, adjust schema, continue |
