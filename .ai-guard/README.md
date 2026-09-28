# .ai-guard — Nugi AI Workspace Protection System

This directory contains the **real NTFS-ACL-based workspace lock** for the `nugi-konten-kreator` repository.

## Purpose

Prevent AI / vibe-coding agents from accidentally modifying protected project files while still allowing free writes inside `output/`.

---

## Files

| File | Description |
|---|---|
| `AI_LOCK.json` | Config: lists `protected_paths` and `always_writable`. Source of truth. |
| `lock.ps1` | **Admin required.** Backs up ACLs, then applies `/deny` write rules. |
| `unlock.ps1` | **Admin required.** Requires typing `UNLOCK`. Removes deny rules, restores ACL backups. |
| `status.ps1` | No elevation needed. Shows lock state + live write-test per path. |
| `backups/` | Timestamped ACL backups created by `lock.ps1`. |
| `lock.state` | JSON state file written by lock/unlock scripts. |

---

## Quick Reference

```powershell
# Check current status (no Admin needed)
.\.ai-guard\status.ps1

# Lock — run in Admin PowerShell
.\.ai-guard\lock.ps1

# Unlock — run in Admin PowerShell, type UNLOCK when prompted
.\.ai-guard\unlock.ps1
```

---

## How It Works

### Lock
1. Reads `AI_LOCK.json` to get the list of protected paths.
2. For each path, saves the current ACL using `icacls /save` → `backups/<timestamp>/<path>.acl`.
3. Applies `icacls /deny` for `(W,D,WATTR,WDAC)` to the **current user** recursively.
4. Verifies `output/` remains writable with a write test.
5. Writes `lock.state`.

### Unlock
1. Reads `lock.state` to confirm workspace is locked.
2. Prompts for explicit `UNLOCK` confirmation.
3. Runs `icacls /remove:d` to strip the deny entries.
4. Optionally restores saved `.acl` backups.
5. Verifies protected paths are writable again.
6. Updates `lock.state`.

### Status
- No elevation required.
- Reads `lock.state` + live-tests write access on every path.

---

## Design Principles

- **Fail closed** — if anything is ambiguous, the script errors and stops.
- **Never elevates the AI agent** — only the PowerShell scripts request Admin.
- **output/ is always writable** — AI agents produce artifacts there freely.
- **ACL backup/restore** — no permanent permission changes; everything is reversible.
- **Explicit unlock confirmation** — type `UNLOCK` to prevent accidental unlocks.

---

## Protected Paths (from AI_LOCK.json)

```
core/          engine/        research/      thinking/
skills/        knowledge/     evaluation/    tests/
docs/          retrieval/     storytelling/
AGENTS.md      .ai-guard/AI_LOCK.json
```

`output/` is **always writable**.
