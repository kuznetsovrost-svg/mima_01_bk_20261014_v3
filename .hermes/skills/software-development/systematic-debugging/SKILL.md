---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, plan, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |
| "I already know the artifact — I'll paraphrase" | For secrets, keys, hashes, tokens, IPs — re-derive from disk (`cat`, `ssh-keygen -lf`, `jq`, `sha256sum`) in the same turn you report or relay it. Hand-quoted values have an unrecoverable failure mode: the user trusts them, pastes them somewhere, and they don't match — wasting a round trip and losing trust in the rest of your report. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Remote Debugging: When the Bug Is on the User's Machine

When the failing system is the user's machine (PowerShell, registry, GUI, DLL) and not your sandbox, you do NOT have direct access to the error. **Phase 1 starts with asking for evidence, not guessing at causes.**

### The Iron Law for Remote Debugging

```
DO NOT LIST POSSIBLE CAUSES WHEN THE USER HAS THE ERROR TEXT AND YOU DO NOT
```

Symptom: user reports "script doesn't work" / "file won't open" / "command failed". Common failure mode is to enumerate 3-5 likely causes and ask "is it one of these?" — that wastes a round trip and forces the user to scan your list. Instead:

- **First response**: ask the user to paste the **exact error text**, exit code, and last command run. Frame it as "I want to see the actual error before guessing — could you copy the full message?"
- **Then**: form ONE hypothesis from the evidence and propose ONE diagnostic command they can run to confirm or refute it.
- **Avoid**: asking the user to "check if X or Y or Z is the issue" — you are the debugger, the user is the source of evidence.

**Mechanism**: each round of guessing without evidence costs a full user turn and accumulates contradictory half-fixes. The error text contains the answer; extracting it once is faster than five iterations of "try this, didn't work?".

### Windows + PowerShell + Non-ASCII Pitfalls

These bit hard when delivering scripts to a Windows user from a Linux/agent environment:

- **PowerShell misparses non-ASCII content unless the file has a UTF-8 BOM.** Without BOM, Cyrillic (and other non-ASCII) is interpreted as CP1251 / Windows-1251 and PowerShell throws "Unexpected token" on string literals. Always save PowerShell scripts that contain non-ASCII with UTF-8 BOM (`[IO.File]::WriteAllBytes(path, [Text.Encoding]::UTF8.GetPreamble() + bytes)`). Verify first 3 bytes are `0xEF,0xBB,0xBF` before delivering.

- **`.\file.ps1` is NOT a typo of `.file.ps1`** — PowerShell's `./` prefix is a backslash, not a forward slash. "term not recognized" can mean the user typed `.file.ps1` (missing `\`) OR is in the wrong directory. First diagnostic: ask for `Get-Location; Test-Path .\file.ps1; Test-Path C:\full\path\file.ps1` output.

- **`Test-Path` returning True + script not found by name = wrong directory, not missing file.** The fix is `& "C:\full\path\file.ps1"` (full path with call operator) or `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\full\path\file.ps1"` from anywhere.

- **DLL bitness mismatch silently fails.** `regsvr32 "X.dll"` from a 32-bit shell won't register a 64-bit DLL (and vice versa). For 64-bit DLLs use `C:\Windows\System32\regsvr32.exe`; for 32-bit use `C:\Windows\SysWOW64\regsvr32.exe`. Verify with `[Environment]::Is64BitProcess` in PowerShell. A 32-bit PowerShell on 64-bit Windows exists and looks identical from the prompt.

- **`regsvr32` error `0x80070016` or "DllRegisterServer not found" = the DLL is .NET, not classic COM.** `regsvr32` only calls `DllRegisterServer`; .NET assemblies do not export it. The right tool is `RegAsm.exe` from .NET Framework: `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe "X.dll" /codebase` (drop `/codebase` if the DLL lives in GAC). Quick tell: open the DLL in Notepad — if it starts with `MZ` followed by a recognizable .NET metadata stream signature, it's a .NET assembly. Don't ship three regsvr32 variants before discovering this.

- **When delivering a script that must be parsed by Windows tools, prefer base64-encoded ASCII installers over heredoc.** Encoded payload survives Telegram / file-copy encoding mangling; a heredoc with Cyrillic does not. Pattern: write the actual script as base64, put the base64 inside an ASCII-only installer script, have the installer decode with `[Convert]::FromBase64String` + `[IO.File]::WriteAllBytes`.

- **Before writing a fix script for a third-party tool integration, run a discovery command first to confirm the integration model.** Don't assume standard patterns (e.g. "this spell-checker is a Microsoft proofing provider" — actually it might be a COM Add-In with a separate `*SpellingProvider.dll` registered via `regsvr32`). Cheap discovery commands (`Get-ChildItem` on the install dir, `Get-ChildItem` on likely registry keys, web search for "<product> <platform> integration architecture") take one tool call and prevent shipping a script that targets the wrong layer. Symptom of skipping this: the script "succeeds" (exit 0, all green checks) but does not actually fix the user's problem.

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
