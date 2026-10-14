---
name: docx
description: Create, read, edit, template, and review Word .docx files.
version: 1.2.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [word, docx, documents, office, templates, revisions, comments]
    category: productivity
    related_skills: [pdf, xlsx, powerpoint]
---

# Docx Skill

Create, read, edit, and template Microsoft Word `.docx` files with
python-docx via small CLIs. It handles text, styles, lists, tables,
images, headers/footers, `{{token}}` templating, tracked changes
(list/accept/reject), comments (list/add/delete), TOC and page-number
fields, and package health checks. It does not render documents itself
(PDF needs LibreOffice — see Converting to PDF) or edit legacy `.doc`.

## When to Use

- The user asks to generate a Word document (report, letter, contract).
- The user hands you a Markdown file and asks for a Word version,
  especially when the source has tables (competitive analysis, inventory
  matrices, capability grids). Markdown tables are the part that breaks
  if you improvise — see "Converting Markdown → DOCX" below.
- You need the text, outline, styles, or embedded images of a `.docx`.
- You must change an existing `.docx`: replace text, edit table cells,
  insert/delete paragraphs, apply styles, merge fragmented runs.
- You have a `.docx` template with `{{placeholders}}` to fill from data.
- The document has tracked changes to review, accept, or reject.
- You need to read reviewers' comments, or add/delete comments.
- A `.docx` won't open or behaves oddly and you need corruption triage.
- The document needs a table of contents or "Page X of Y" footers.
- Not for: `.doc` (legacy), `.odt`, or WYSIWYG layout work.

## Prerequisites

- Python 3.10+ with `python-docx` installed:
  `pip install python-docx` (import name is `docx`; lxml comes with it).
- Comments `add` uses the native API on python-docx >= 1.2 and an XML
  fallback on older versions — both are automatic.
- For image blocks: the image files must exist locally (PNG/JPEG).

## How to Run

All helpers live in `scripts/` next to this file. Run them with the
`terminal` tool; each supports `--help` and prints JSON to stdout.

```bash
python scripts/docx_create.py spec.json out.docx
python scripts/docx_read.py out.docx --text
python scripts/docx_edit.py replace out.docx --find old --replace new
python scripts/docx_template.py tpl.docx values.json filled.docx
python scripts/docx_revisions.py list out.docx
python scripts/docx_comments.py list out.docx
python scripts/docx_validate.py out.docx
```

## Quick Reference

| Task | Command |
| --- | --- |
| Create from JSON spec | `docx_create.py spec.json out.docx` |
| Full text (body+tables+headers/footers) | `docx_read.py f.docx --text` |
| Heading outline + table shapes | `docx_read.py f.docx --structure` |
| Styles actually used | `docx_read.py f.docx --styles` |
| Extract embedded images | `docx_read.py f.docx --images outdir/` |
| Detect tracked changes/comments | `docx_read.py f.docx --revisions` |
| Find/replace (formatting kept) | `docx_edit.py replace f.docx --find A --replace B -o out.docx` |
| Set a table cell | `docx_edit.py set-cell f.docx --table 0 --row 1 --col 2 --text X` |
| Insert paragraph before index N | `docx_edit.py insert f.docx --index N --text X --style Normal` |
| Delete paragraph N | `docx_edit.py delete f.docx --index N` |
| Apply style to paragraph N | `docx_edit.py style f.docx --index N --style "Heading 1"` |
| Merge equal-format adjacent runs | `docx_edit.py normalize f.docx -o out.docx` |
| Insert TOC field before para N | `docx_edit.py toc f.docx --index N -o out.docx` |
| "Page X of Y" footer fields | `docx_edit.py page-numbers f.docx` |
| Fill `{{tokens}}` | `docx_template.py tpl.docx values.json out.docx --strict` |
| List revisions (id/author/date/text) | `docx_revisions.py list f.docx` |
| Accept / reject all revisions | `docx_revisions.py accept-all f.docx -o out.docx` (or `reject-all`) |
| Accept / reject one revision | `docx_revisions.py accept f.docx --id 3 -o out.docx` |
| List comments (+anchored text) | `docx_comments.py list f.docx` |
| Add comment anchored to text | `docx_comments.py add f.docx --target "phrase" --text "note" --author You` |
| Delete comment by id | `docx_comments.py delete f.docx --id 0` |
| Health-check the package | `docx_validate.py f.docx` (exit 1 on errors) |

## Procedure

1. **Create.** Write a JSON spec with `write_file`, then run
   `scripts/docx_create.py`. The spec supports: `page` (size + margins in
   mm), `header`/`footer` strings, `footer_page_numbers` (adds a
   "Page X of Y" field footer), `styles` (custom paragraph styles with
   font, size, bold/italic, hex `color`), and `blocks` — `heading`
   (level 1-9), `paragraph` (either `text` or a `runs` list where each run
   may set `bold`/`italic`/`underline`), `bullet_list`, `numbered_list`,
   `table` (`header` row rendered bold, `rows`, optional built-in table
   `style` such as `Table Grid`), `image` (`path`, optional `width_mm`),
   `toc` (Table of Contents field), and `page_break`. The full spec
   format is documented at the top of `scripts/docx_create.py`.
2. **Read.** Use `scripts/docx_read.py` with exactly one mode flag.
   `--text` returns body paragraphs, all table cell text, and
   header/footer text as JSON. `--structure` returns the heading outline
   plus paragraph/table/section counts. `--images DIR` copies every file
   under `word/media/` out of the package.
3. **Edit.** Use `scripts/docx_edit.py`. `replace` walks body, tables
   (nested included), headers and footers, and preserves run formatting;
   add `--body-only` to skip headers/footers. Pass `-o out.docx` to keep
   the original; omit it to edit in place. Paragraph indices for
   `insert`/`delete`/`style`/`toc` refer to `--structure`/`--text` body
   order. Run `normalize` first on documents that came out of heavy Word
   editing — it merges adjacent runs with identical formatting so later
   find-replace matches reliably.
4. **Review revisions.** `docx_revisions.py list` reports every `w:ins`
   and `w:del` (id, author, date, affected text) anywhere in body,
   tables, headers, or footers. `accept-all` / `reject-all` resolve them
   in bulk; `accept`/`reject --id N` handles a single revision. Accept
   keeps insertions and drops deleted text; reject does the reverse.
5. **Comments.** `docx_comments.py list` returns each comment's id,
   author, date, body text, and the document text it is anchored to.
   `add --target "some phrase"` anchors a new comment to the first
   occurrence of that phrase (runs are split as needed; formatting is
   preserved). `delete --id N` removes the comment and its markers
   without touching document text.
6. **Template.** Put `{{name}}`-style tokens in the document. Run
   `scripts/docx_template.py` with a JSON object of values. Use
   `--strict` to fail when tokens remain unfilled; the JSON output lists
   `filled` counts and `unfilled_tokens` either way.
7. **Verify** (always): re-read the output with `--text` or
   `--structure`, and run `docx_validate.py` on anything you produced
   via revision/comment surgery.

## Converting to PDF

No script needed. When LibreOffice is installed, convert headlessly:

```bash
soffice --headless --convert-to pdf --outdir outdir/ file.docx
```

Check availability first (`command -v soffice || command -v
libreoffice`). If neither exists, tell the user PDF conversion is
unavailable in this environment rather than improvising — python-docx
cannot render PDFs, and layout fidelity requires a real renderer.

## Converting Markdown → DOCX

When the user hands you a `.md` file (especially one with tables) and
asks for a Word version, the reliable pipeline is **Pandoc for the
structural conversion + python-docx for table styling**. Pandoc alone
produces a working `.docx` but tables have no shading, header rows
are not bolded, and headers land in the "Source Code" style. The two
steps take ~5 seconds total; the result opens in Word and looks like
a real document.

### Install once

```bash
apt-get install -y pandoc          # Debian/Ubuntu; macOS: brew install pandoc
pip install python-docx           # already in this skill's prerequisites
```

Pandoc is **not** optional. The earlier reflex "convert via the docx
spec JSON" works for clean authored documents but fails on real-world
Markdown with mixed content (tables, code blocks, task lists, blockquotes)
because `docx_create.py` does not parse Markdown — it accepts a JSON
spec only. Pandoc handles all of that natively.

### Step 1 — structural conversion

```bash
pandoc SOURCE.md \
  -f markdown+pipe_tables+grid_tables+task_lists \
  -t docx \
  -o intermediate.docx
```

The `+pipe_tables` and `+grid_tables` extensions are what makes tables
land as native Word tables instead of being broken into tab-separated
paragraphs. For documents with checkbox lists add `+task_lists`.
Without these, Markdown tables render as lines of pipe-delimited text
and the result is unreadable.

### Step 2 — style tables and headings via python-docx

Pandoc's default template applies minimal styling. Real users want:

- Header row: bold + light fill (e.g. `D9E1F2`)
- Data rows: smaller font (9–10pt) so wide tables fit on A4
- Visible borders (default Pandoc tables are borderless)
- Headings styled to match the body (Pandoc maps them to "Source Code" by
  default in the default template; assign Heading 1/2/3 sizes)

```python
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document("intermediate.docx")
styles = {s.name: s for s in doc.styles}

# Map heading sizes — the defaults are tiny when Pandoc emits them
for h_name, size in [("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 12)]:
    if h_name in styles:
        s = styles[h_name]
        s.font.name = "Calibri"
        s.font.size = Pt(size)
        s.font.bold = True

# Style every table: bold + shaded header row, smaller data font, borders
for tbl in doc.tables:
    # Header row — bold + light-blue fill
    for cell in tbl.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
                if run.font.size is None:
                    run.font.size = Pt(10)
        tc_pr = cell._tc.get_or_add_tcPr()
        for old in tc_pr.findall(qn("w:shd")):
            tc_pr.remove(old)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "D9E1F2")
        tc_pr.append(shd)
    # Data rows — smaller font
    for row in tbl.rows[1:]:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    if run.font.size is None:
                        run.font.size = Pt(9)
    # Visible borders
    tbl_pr = tbl._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "808080")
        borders.append(b)
    tbl_pr.append(borders)

doc.save("out.docx")
```

### Verification

After saving, the table count and column count tell you immediately
whether Pandoc actually found the tables:

```python
from docx import Document
doc = Document("out.docx")
print(f"tables: {len(doc.tables)}, max_cols: {max(len(t.columns) for t in doc.tables)}")
# Expect: tables=N where N matches the Markdown source's table count;
#         max_cols matches the widest source table.
```

A 0-table result after a known-Markdown-with-tables input means
Pandoc did not parse the tables — most often the `+pipe_tables`
extension is missing or the source uses non-pipe syntax (CSV inside
fenced blocks, ASCII alignment, etc.). Confirm by reading the source
with `head` and checking that table rows really start with `|`.

### When to skip this pipeline

- The user only wants the **plain text** of the Markdown → use
  `web_extract` or `read_file` and stop there.
- The user wants a **specific Word template** applied → use
  `scripts/docx_template.py` after Pandoc to inject `{{tokens}}`,
  or skip Pandoc and build directly from JSON spec via
  `scripts/docx_create.py`.
- The Markdown source has **no tables** → Pandoc's defaults are
  fine, no Python post-processing needed.

## Pitfalls

- **Tokens split across runs.** Word often fragments text into several
  runs. The replace helpers collapse matched runs (replacement inherits
  the first run's formatting); running `docx_edit.py normalize` first
  reduces fragmentation for all later edits.
- **Revision coverage.** `docx_revisions.py` resolves run-level
  insertions and deletions (the overwhelming majority). Paragraph-mark
  and table-row revisions, format-change records, and moves are detected
  by `--revisions` but not auto-resolved — see
  `references/revisions-and-comments.md` and hand those to Word.
- **Comment threading.** Replies and "resolved" status live in
  `commentsExtended.xml`, which this skill ignores; comments it adds are
  plain top-level comments.
- **Field results are computed by Word.** `toc`, `page-numbers`, and the
  `toc`/`footer_page_numbers` spec options write *field codes*.
  Word/LibreOffice populates the actual entries and numbers when the
  file is opened (Word may prompt to update fields); python-docx never
  computes them, so placeholder text shows until then.
- **Validation is a health check, not schema validation.**
  `docx_validate.py` verifies the zip, required parts, relationship
  targets, image magic bytes, and referenced styles. It is NOT XSD
  validation — a file can pass and still contain XML Word dislikes.
- **Style names must exist.** Applying a style that isn't defined in the
  document raises `KeyError`. Built-ins like `Heading 1`, `List Bullet`,
  `List Number`, `Table Grid` exist in the default template; custom
  styles must be declared in the create spec first.
- **Numbered lists restart.** `List Number` relies on Word's default
  numbering; separate lists in one document may continue numbering
  instead of restarting. Warn users needing precise multi-list numbering.
- **Cell writes replace formatting.** `set-cell` uses `cell.text = ...`,
  which resets runs in that cell to plain formatting.
- **Encoding.** All JSON specs/values files are read as UTF-8 explicitly;
  never rely on locale defaults when writing your own glue code.
- **Don't unzip-and-sed the XML.** Edit through the scripts (or
  python-docx); raw text substitution in `document.xml` corrupts files
  easily. Use `patch`/`write_file` only for the JSON inputs, never on the
  `.docx` itself.
- **Style lookup with `doc.styles['Heading 1']` raises KeyError.** The
  style IS defined, but `styles[]` on python-docx uses internal style IDs,
  not display names. Build a name→style map first:
  `style_map = {s.name: s for s in doc.styles}; s = style_map["Heading 1"]`.
  The map's keys are display names ("Heading 1", "Block Text",
  "Compact") which is what you can read with `read_file` or
  `docx_read.py --styles`. Same shape applies to any built-in style
  access ("List Bullet", "Table Grid", "Caption").

## Verification

- After create/edit/template, run `docx_read.py out.docx --text` and
  check the expected strings appear (and old strings are gone).
- After accept/reject, `docx_revisions.py list` should return `[]` (or
  only the ids you intentionally left); after comment surgery,
  `docx_comments.py list` should reflect the change and `--text` output
  must be unchanged.
- `docx_validate.py out.docx` exits 0 with `"ok": true` on a healthy
  package — run it after any revision/comment/field manipulation.
- For templates run with `--strict`, or check `unfilled_tokens == []`.
- Structure checks: `--structure` should show the expected heading
  outline and table shapes; `--styles` confirms custom styles applied.
