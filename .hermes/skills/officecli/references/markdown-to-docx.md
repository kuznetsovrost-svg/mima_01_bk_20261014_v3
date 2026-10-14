# Markdown → DOCX (when `officecli` is not enough)

`officecli` operates on existing `.docx`. It does **not** parse Markdown. When the user asks "сформатируй .md в .docx" / "пришли в Word" / "send as DOCX", use `python-docx` instead.

This is a support reference for the conversion direction. The reverse (`officecli` reading the resulting `.docx`) goes back through the normal `officecli` workflow.

## Why this lives here

The class trigger is "convert or deliver a Markdown file as a Word document". The natural instinct is to load `officecli`. That instinct is wrong for the conversion direction — `officecli`'s `create` produces an empty `.docx` you'd have to populate by hand.

## Install (one-time)

```bash
pip install python-docx           # currently 1.2.0
```

`pandoc` is the higher-quality option if it's installed:

```bash
apt-get install -y pandoc
pandoc input.md -o output.docx --from markdown+pipe_tables+grid_tables+task_lists
```

Verified 2026-09-24 on a 89 KB Russian-language Markdown with 25 tables (incl. 14-column matrix): pandoc converted all tables natively (no manual parsing), preserved emoji 🟡❌✅, and produced a 43 KB DOCX in one pass. Use pandoc FIRST; fall back to python-docx only for missing-edge-case files or for styling headers/footers/table colors that pandoc doesn't control.

### When to use pandoc vs python-docx

| Case | Tool | Why |
|---|---|---|
| MD with tables (any size, esp. wide matrix tables) | **pandoc** | native DOCX table conversion, preserves column widths |
| MD → DOCX with code blocks, lists, headings | **pandoc** | native DOCX styles, cleaner than reimplementing |
| Need styled tables (header bold + colored fill + borders) | **pandoc then python-docx** | pandoc for layout, python-docx post-processing for styling |
| MD with custom inline-run parsing (`**bold**`, `*italic*`) that pandoc ignores | python-docx | pandoc handles `**bold**` natively, but if you need a custom transform, python-docx gives full control |
| DOCX → MD | pandoc only | python-docx can't easily extract to MD |

### Styling pandoc output with python-docx (post-process)

After `pandoc` produces the DOCX, load it and apply table styling that pandoc doesn't provide by default:

```python
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document('/tmp/report.docx')

# pitfall: doc.styles is iterable but NOT dict-like — must look up by iterating
style_map = {s.name: s for s in doc.styles}

for h_name, size in [('Heading 1', 18), ('Heading 2', 14), ('Heading 3', 12)]:
    if h_name in style_map:
        s = style_map[h_name]
        s.font.name = 'Calibri'
        s.font.size = Pt(size)
        s.font.bold = True

# Header row of each table: bold + light-blue fill + bordered
for tbl in doc.tables:
    for cell in tbl.rows[0].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True
                if run.font.size is None:
                    run.font.size = Pt(10)
        tc_pr = cell._tc.get_or_add_tcPr()
        for old in tc_pr.findall(qn('w:shd')):
            tc_pr.remove(old)
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'D9E1F2')
        tc_pr.append(shd)
    # Borders
    tbl_pr = tbl._tbl.tblPr
    for old in tbl_pr.findall(qn('w:tblBorders')):
        tbl_pr.remove(old)
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        b = OxmlElement(f'w:{edge}')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), '4')
        b.set(qn('w:color'), '808080')
        borders.append(b)
    tbl_pr.append(borders)

doc.save('/tmp/report-styled.docx')
```

**Pitfall**: `doc.styles['Heading 1']` raises `KeyError`. The styles collection is iterable but not subscriptable by name — build a `{s.name: s}` map first.

## The converter

Working recipe (verified 2026-08-05 on `Проект_агента_для_ЦОРПУ.docx` — 19 KB MD → 44 KB DOCX, 73 paragraphs, 7 tables):

```python
import os, re
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

src, dst = '/root/<file>.md', '/root/<file>.docx'
md_content = open(src, encoding='utf-8').read()

doc = Document()
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

# Margins
section = doc.sections[0]
for attr in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
    setattr(section, attr, Inches(0.9))

# Inline-runs parser for **bold**
def add_runs(p, text):
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            r = p.add_run(part[2:-2]); r.bold = True
        else:
            p.add_run(part)

lines = md_content.split('\n')
i = 0
while i < len(lines):
    line = lines[i].rstrip()
    if not line:
        i += 1; continue

    # Headings H1-H4
    if line.startswith('# '):  doc.add_heading(line[2:], level=1); i += 1; continue
    if line.startswith('## '): doc.add_heading(line[3:], level=2); i += 1; continue
    if line.startswith('### '):doc.add_heading(line[4:], level=3); i += 1; continue
    if line.startswith('#### '):doc.add_heading(line[5:], level=4); i += 1; continue

    # Horizontal rule
    if re.match(r'^-{3,}$|^={3,}$|^\*{3,}$', line):
        i += 1; continue

    # Code block
    if line.startswith('```'):
        i += 1
        code = []
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code.append(lines[i]); i += 1
        if i < len(lines): i += 1
        if code:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            run = p.add_run('\n'.join(code))
            run.font.name = 'Consolas'; run.font.size = Pt(9)
            # Light gray background
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), 'F3F4F6')
            pPr.append(shd)
        continue

    # Blockquote
    if line.startswith('> '):
        doc.add_paragraph(line[2:], style='Intense Quote'); i += 1; continue

    # List (consecutive items)
    if re.match(r'^(\d+\.|-|\*)\s+', line):
        items, list_re = [], re.compile(r'^(\d+\.|-|\*)\s+(.*)')
        ordered = True
        while i < len(lines) and (m := list_re.match(lines[i].rstrip())):
            if not re.match(r'^\d+\.', m.group(1)): ordered = False
            items.append(m.group(2)); i += 1
        for text in items:
            doc.add_paragraph(text, style='List Number' if ordered else 'List Bullet')
        continue

    # Table (header line + separator line + data lines)
    if '|' in line and i + 1 < len(lines) and re.match(r'^\|?[\s\-:|]+\|?$', lines[i+1].strip()):
        rows = [[c.strip() for c in line.split('|')]]
        i += 2  # skip header + separator
        while i < len(lines) and '|' in lines[i] and lines[i].strip():
            rows.append([c.strip() for c in lines[i].split('|')]); i += 1
        # Trim empty leading/trailing cells
        rows = [(r[1:-1] if r and not r[0] else r) for r in rows]
        n_cols = max(len(r) for r in rows)
        table = doc.add_table(rows=len(rows), cols=n_cols)
        table.style = 'Light Grid Accent 1'
        for r_idx, row in enumerate(rows):
            for c_idx in range(n_cols):
                cell = table.cell(r_idx, c_idx)
                cell.text = ''
                run = cell.paragraphs[0].add_run(row[c_idx] if c_idx < len(row) else '')
                if r_idx == 0: run.bold = True
                run.font.size = Pt(10)
        continue

    # Regular paragraph (may include **bold**)
    para_lines = [line]; i += 1
    while i < len(lines) and lines[i].rstrip() and not (
        lines[i].startswith(('#', '>', '|', '```')) or re.match(r'^(\d+\.|-|\*)\s', lines[i].rstrip())):
        para_lines.append(lines[i].rstrip()); i += 1
    p = doc.add_paragraph()
    add_runs(p, ' '.join(para_lines))

doc.save(dst)
print(f'OK: {dst} ({os.path.getsize(dst):,} B)')
```

## What it covers (the 8-element subset the user actually uses)

| Markdown element | DOCX mapping |
|---|---|
| `# H1` / `## H2` / `### H3` / `#### H4` | Heading 1/2/3/4 |
| `> blockquote` | Intense Quote |
| ` ```code``` ` | Consolas 9pt, gray-shaded background |
| `**bold**` (inline) | Bold run |
| `- item` | List Bullet |
| `1. item` | List Number |
| `\| table \|` | Real `doc.add_table` with bold header row |
| `---` | Skipped (no good DOCX equivalent) |

## What it does NOT cover (extend if needed)

| Element | Add when user actually asks |
|---|---|
| `*italic*`, `~~strike~~` | Inline-run parser branch |
| `[text](url)` | `add_hyperlink` helper (not in `python-docx` stdlib) |
| Images `![alt](url)` | `add_picture` with download |
| ` ```python ` fenced code with language | Just keep Consolas — language-specific highlighting is overkill |
| Nested lists | Walk the list lines and track indent |
| Footnotes `[^1]` | DOCX footnotes via XML manipulation |

The user has not asked for any of these yet. Don't over-engineer.

## Delivery

After conversion, deliver as normal:

```bash
TOK=$(grep '^TELEGRAM_BOT_TOKEN=' /root/.hermes/.env | cut -d= -f2- | tr -d '\n')
curl -sS -F document=@"/root/<file>.docx" -F chat_id=505586502 \
     "https://api.telegram.org/bot${TOK}/sendDocument"
```

Size: MD ~19 KB → DOCX ~44 KB is typical (DOCX is heavier due to XML overhead).

## Related

- `officecli/SKILL.md` — the main `officecli` skill (read/edit existing .docx)
- `guide-authoring-for-hermes` — the Russian-language guide + Telegram delivery workflow
