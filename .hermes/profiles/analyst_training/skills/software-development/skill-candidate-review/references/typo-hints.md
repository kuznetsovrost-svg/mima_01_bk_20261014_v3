# Typo Hints for Skill Body Review

This list is empirical — add to it as new patterns surface during reviews.
The scan is **advisory**: false positives are expected and should be flagged
as such in the report rather than silently dropped.

## Cyrillic / Latin homoglyphs

These characters look identical to Latin letters but are encoded as Cyrillic.
They survive cut-paste between keyboards and break search, validation, and
slug-based routing.

| Looks like | Cyrillic | Latin | Notes |
|---|---|---|---|
| а | U+0430 | U+0061 | Most common offender in "аcademic", "аnalysis" |
| е | U+0435 | U+0065 | "матeматика", "имe" |
| о | U+043E | U+006F | "кoмпания" |
| р | U+0440 | U+0070 | "рrogram", "рython" |
| с | U+0441 | U+0063 | "сourse", "сontent" |
| у | U+0443 | U+0079 | "уou", "уes" |
| х | U+0445 | U+0078 | "хello" |

**Detection:** scan all string fields (especially `name`, `slug`, file paths
in body) with `unicodedata.name(ch)` and flag any `ch` whose name contains
"CYRILLIC".

## Common Russian-language slips (in Cyrillic body prose)

These are *doubled consonant* or *wrong suffix* patterns a Russian-speaking
author produces when typing fast.

| Wrong | Right | Notes |
|---|---|---|
| утвержденние | утверждение | doubled "нн" |
| прохожденния | прохождения | doubled "нн" + "ия" |
| обоснованнно | обоснованно | doubled "н" |
| проаграммы | программы | "агр" instead of "огр" |
| преметы | предметы | dropped "д" |
| аритекторов | архитекторов | dropped "х" |
| соотоветствует | соответствует | doubled "о" |

## Path / filename slips

| Wrong | Right | Context |
|---|---|---|
| Otputs | Outputs | directory/filename in verification checklist |
| Outpusts | Outputs | same |
| sсhemas | schemas | Cyrillic "с" |
| cademic | academic | Cyrillic "а" |
| trainig | training | dropped "n" |

## Scanning strategy

1. Read the entire body into a string.
2. For each line, do a case-insensitive substring scan against this list.
3. For Cyrillic homoglyphs, do a character-by-character check on slug-like
   fields (`name`, anything that looks like `kebab-case-id`).
4. Output a table with line numbers — the user fixes in one pass with their
   editor's "go to line".
5. Mark false positives explicitly so the user doesn't second-guess them.

## Anti-pattern: don't auto-correct

The scan reports. It does not edit. The user decides whether `обоснований`
is a typo or correct genitive case. Auto-correction here would silently
break valid Russian prose.