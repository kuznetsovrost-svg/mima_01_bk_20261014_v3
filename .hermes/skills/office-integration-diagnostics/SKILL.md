---
name: office-integration-diagnostics
description: Diagnose Office/COM/.NET Windows integration before fixing.
---

# Office Integration Diagnostics on Windows

## When to use
Writing a PowerShell script to fix an integration issue: spell-checker (ORFO, LanguageTool), Outlook add-in, Visual Studio extension, IDE plugin, COM component, or any third-party tool that hooks into Office/Windows.

## Why this skill exists
**2026-09-28 lesson (ORFO case):** First script "restored proofing provider" via COM Word API + registry. Useless — ORFO at the user's PC works as **native COM Add-In** (`OrfoAddin2012.dll` + `ORFOSpellingProvider.dll` registered via `regsvr32`), NOT as a proofing provider. Wasted 4 iterations before discovering real architecture.

## Diagnostic ladder — run BEFORE writing fix

Always run these 3-5 commands FIRST. Results tell you the architecture:

```powershell
# 1. Where is the product installed?
Get-ChildItem "C:\Program Files\*" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "*<ProductName>*" } |
    Select-Object FullName, Length, LastWriteTime | Format-Table

# 2. Is there an Add-In registered?
Get-ChildItem "HKLM:\Software\Microsoft\Office\Word\Addins" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $props = Get-ItemProperty $_.PSPath
        Write-Host "$($_.PSChildName): LoadBehavior=$($props.LoadBehavior), Manifest=$($props.Manifest)"
    }

# 3. Is there a Proofing Tool registered?
$pt = @("HKLM:\SOFTWARE\Microsoft\Office\16.0\Word\ProofingTools",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Office\16.0\Word\ProofingTools",
        "HKCU:\SOFTWARE\Microsoft\Office\16.0\Word\ProofingTools")
foreach ($p in $pt) {
    if (Test-Path $p) { Get-ChildItem $p | ForEach-Object { Write-Host "$($_.PSChildName): ProviderName=$((Get-ItemProperty $_.PSPath).ProviderName)" } }
}

# 4. What's the architecture of the main DLL? (NET or native?)
$bytes = [System.IO.File]::ReadAllBytes("path\to\main.dll")
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
$machine = [BitConverter]::ToUInt16($bytes, $peOffset + 4)
Write-Host "Machine: 0x$($machine.ToString('X4'))"   # 0x14c=x86, 0x8664=x64

# 5. Is it a .NET assembly? (look for mscoree.dll dependency or COM descriptor)
# If .NET -> needs RegAsm.exe
# If native COM -> needs regsvr32
# If plain service/exe -> just config file

# 6. Check what version of Office
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration" |
    Select-Object Platform, VersionToReport

# 7. Check architecture match (32-bit Office needs 32-bit add-in)
[Environment]::Is64BitProcess   # PowerShell arch
```

## Architecture → fix matrix

| What you find | Fix to apply |
|---|---|
| Add-In with `LoadBehavior=0` | Set `LoadBehavior=3` via registry |
| Add-In with `Manifest=*.vsto` | .NET VSTO — regsvr32 won't work, check VSTO runtime |
| ProofingTools\<lcid>\ProviderName exists but broken path | Fix path in registry |
| `*.dll` is native COM (`regsvr32` succeeds) | Done |
| `*.dll` is .NET (RegAsm succeeds) | Done |
| `regsvr32` fails with 0x80070016 | Check dependencies via Dependencies.exe or dumpbin |
| `RegAsm` fails with RA0000 "not a valid .NET assembly" | Not .NET — try `regsvr32` instead |
| DLL works as COM but Word doesn't see it | May need manual registry entries in `ProofingTools\<lcid>\` |

## PowerShell + Telegram gotcha (2026-09-28)

`.ps1` files sent via Telegram arrive with broken encoding on Windows → `Unexpected token` on cyrillic lines. **Always write scripts in pure ASCII** when shipping via Telegram:

- All variable names, regex patterns, file paths: ASCII
- Cyrillic only in comments or in `@'...'@` base64 blobs
- If you need cyrillic in messages: pass via `$variable` set from base64

Windows PowerShell default ExecutionPolicy = `Restricted`. Always launch with:
```
powershell -NoProfile -ExecutionPolicy Bypass -File path.ps1
```
Or set once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass`.

To repair an already-broken file from PowerShell:
```powershell
$bytes = [System.Text.Encoding]::UTF8.GetPreamble() + [System.Text.Encoding]::UTF8.GetBytes($content)
[System.IO.File]::WriteAllBytes($path, $bytes)
```

## Common Office product locations to check

| Product | Typical install path |
|---|---|
| ОРФО 2016 | `C:\Program Files\Informatic\ORFO 2016\` |
| LanguageTool | `C:\Program Files\LanguageTool\` or browser extension |
| Abbyy FineReader | `C:\Program Files\ABBYY FineReader *\` |
| SolidWorks | `C:\Program Files\SOLIDWORKS Corp\` |
| 1Password | `C:\Users\<u>\AppData\Local\1Password\` |

## When you STILL can't fix it

If `regsvr32`, `RegAsm`, manual registry, and setup re-run all fail:
1. Check DLL dependencies with `Dependencies.exe` (https://github.com/lucasg/Dependencies)
2. Check for missing runtime (VC++ Redistributable, .NET Framework version)
3. Check Windows Event Viewer → Application log for module load errors
4. Try `procmon` from Sysinternals to watch what registry/files the loader touches

Don't write a 4th iteration of "registry fixes" — escalate to dependency analysis.

---

## Vendor-specific recovery commands (concrete patterns)

Many vendor setups ship silent registration switches. **Always check the vendor's own setup exe for `/?` first** before writing custom reg-fix scripts — vendor logic is more complete than anything you'll patch by hand.

Common flags to try:
- `/register` — re-register COM components without full reinstall (ORFO, many Adobe COM add-ins)
- `/repair` — restore missing registry entries from installed files
- `/silent` — run without UI prompts (ORFO `OrfoUpdate.exe`)
- `/unregister` — the inverse, useful for clean state before re-register

For ORFO specifically: `OrfoSetup2.exe /register` from `C:\Program Files\Informatic\ORFO 2016\` re-registers `ORFOSpellingProvider.dll` and friends. Quiet success = no output, exit 0. If exit 0 but Word still doesn't see it, the next layer is Word Trust Center (see "Add-In enabled but invisible" below).

---

## Add-In enabled but invisible in Word UI

`LoadBehavior=3` in registry + valid `.vsto` manifest on disk **does NOT guarantee Word loads it.** The common hidden cause: **Trust Center → Add-ins → Disabled Items**.

The user must open Word manually:
`File → Options → Trust Center → Trust Center Settings → Add-ins → Manage: Disabled Items → Go`
Find the add-in in the list → select → "Enable" → restart Word.

This is a UI-only operation. No PowerShell can re-enable a Trust-Center-disabled add-in remotely. If the user reports "the fix didn't work" but you only changed LoadBehavior, this is almost always why.

---

## Common error codes seen in practice

| Error | Tool | Means |
|---|---|---|
| `0x80070016` | `regsvr32` | `DllRegisterServer` missing or failed — DLL is either not self-registrable, has missing dependencies, or is actually a VSTO/.NET add-in masquerading as COM |
| `0x80070005` | `regsvr32` / RegAsm | Access denied — needs admin elevation |
| `0x80004005` | `regsvr32` | Unspecified failure — usually dependency or version mismatch |
| `RA0000: not a valid .NET assembly` | `RegAsm` | DLL is native COM, not .NET — switch to `regsvr32` |
| `0x80131018` | `RegAsm` | .NET Framework version mismatch (assembly built for newer/older runtime) |

---

## CMD-vs-PowerShell cross-contamination pitfall

Users copy commands from documentation / chat without noticing the shell. Two recurring mistakes:

1. **CMD `cd /d C:\Foo` pasted into PowerShell** → `Set-Location : A positional parameter cannot be found that accepts argument '/d'`. PowerShell's `Set-Location` has no `/d` switch. Fix: just `cd C:\Foo` in PowerShell, or wrap with `cmd /c "cd /d C:\Foo && ..."` if you really need CMD semantics.
2. **PowerShell `$env:VAR = "x"` pasted into CMD** → silent no-op. CMD uses `set VAR=x`.

When sending commands to the user, **state the shell explicitly** in the instruction line. When debugging a "command not found" error, first ask "which shell are you pasting this into?"

---

## Inline one-liner pattern (when file delivery fails)

When `.ps1` delivery via Telegram / chat / clipboard corrupts encoding, **fall back to inline one-liners** instead of fighting the file transfer. User pastes the one-liner directly into their PowerShell window.

Recipe for a multi-step diagnostic as a single line (semicolons as separators):

```powershell
$paths = @("HKLM:\SOFTWARE\Microsoft\Office\Word\Addins", "HKCU:\Software\Microsoft\Office\16.0\Word\Addins"); foreach ($p in $paths) { if (Test-Path $p) { Get-ChildItem $p -EA SilentlyContinue | ForEach-Object { $props = Get-ItemProperty $_.PSPath -EA SilentlyContinue; Write-Host "[$($_.PSPath)] $($props.FriendlyName) LoadBehavior=$($props.LoadBehavior) Manifest=$($props.Manifest)" } } }
```

Rules for inline commands:
- Use `-EA SilentlyContinue` instead of `-ErrorAction SilentlyContinue` (shorter, less to type)
- `;` between statements, no newlines
- `Write-Host` instead of `Write-Output` so output is immediate
- Avoid `Read-Host` in inline commands (blocks the shell)
- ASCII patterns only — cyrillic in patterns breaks silently when user copy-pastes through certain buffers

Inline commands are a **rescue channel**, not the default. Prefer delivering `.ps1` files (cleaner, reusable, can be re-run) — but keep the inline pattern ready when delivery fails.

---

## .vsto manifest tells you the architecture

When you see `Manifest=...\foo.vsto|vstolocal` in the add-in registry, the `.vsto` is a ClickOnce application manifest. Open it and look for `processorArchitecture`:

- `msil` → .NET VSTO add-in (needs VSTO runtime + sometimes ClickOnce trust)
- `x86` / `x64` → native VSTO shim around a native DLL

`processorArchitecture="msil"` is the ORFO case. VSTO add-ins are NOT registered via `regsvr32` (native COM) NOR `RegAsm` (pure .NET assembly) — they're loaded by VSTO runtime reading the `.vsto`. If regsvr32 and RegAsm both fail with "not a valid XYZ assembly", suspect VSTO and check:

```powershell
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VSTO Runtime Setup\v4" -ErrorAction SilentlyContinue
```

If empty → VSTO runtime missing or wrong version → real fix is `OrfoSetup2.exe /repair` or vendor MSI, not registry editing.

---

## Session-exit hand-off

When you've found the diagnosis but not the fix (e.g., user must click through Word Trust Center, or vendor must ship a new build), capture:

- The exact diagnostic commands you ran + the answers
- The architecture conclusion (COM / VSTO / native / .NET)
- What you tried + why each attempt failed
- What the user needs to do manually (and why no PowerShell can do it)

Put this in `/tmp/<topic>/notes/handoff.txt` so the next session (or the user coming back tomorrow) doesn't re-run the diagnostic ladder from scratch.
