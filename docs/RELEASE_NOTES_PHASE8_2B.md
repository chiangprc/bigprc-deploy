# Phase 8.2B — Rule Simulation Release Notes

> **Tag**: `v0.8.2b-rule-simulation`
> **Date**: 2026-07-28
> **Status**: Stable

---

## Objective

Allow editors to simulate rule_json changes before applying them. The editor modifies a rule (add tags/tags_or, or replace entirely), sees the delta of matched resources, then decides whether to proceed with the actual `--propose` → `--apply` flow.

## Design Principles

- **Read-only**: No database writes. No file creation. Terminal output only.
- **Reuses Engine**: Calls `rule_engine.match_collection()` — no duplicated logic.
- **CLI Only**: No web UI, no API. Respects CLI → JSON → Static HTML architecture.
- **Guidance, not automation**: Shows evidence. Editor decides.

## CLI Usage

```bash
# Add a single tag to tags_or
python3 collection_rule_assist.py --simulate bbc-nature --add-tags-or 海洋

# Add a tag to tags AND group
python3 collection_rule_assist.py --simulate bbc-nature --add-tags BBC

# Full rule replacement
python3 collection_rule_assist.py --simulate bbc-nature \
  --rule '{"tags":["BBC"],"tags_or":["海洋","自然"]}'

# --rule takes priority over --add-* parameters
```

## Safety Constraints

| Constraint | Enforcement |
|-----------|-------------|
| No database writes | `cmd_simulate()` contains no INSERT/UPDATE/DELETE/commit() |
| No file creation | No `open()` or `.write()` calls |
| No draft JSON | Simulation result is transient, displayed in terminal only |
| Matches use Rule Engine | `from rule_engine import match_collection` — no duplicated logic |
| Graceful errors | Missing collection, invalid JSON, parse failures → `sys.exit(1)` with message |

## Test Results

| Test | Result |
|------|--------|
| `--add-tags-or` correctly appends tag | PASS |
| `--add-tags` correctly appends tag | PASS |
| `--rule` replaces entire rule | PASS |
| `--rule` priority over `--add-*` | PASS |
| Nonexistent collection → error | PASS |
| Invalid JSON → error | PASS |
| collections table unchanged after simulation | PASS |
| resource_collections unchanged after simulation | PASS |
| No draft files created | PASS |

## Current Limitations

- Single-collection only (no bulk simulation)
- No `--remove-tags` / `--remove-tags-or` parameters (edit the full rule via `--rule` instead)
- Terminal output only (not displayed in admin dashboard)
- No history/persistence of simulation results
