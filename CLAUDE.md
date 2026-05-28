# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->


## Build & Test

- No install step — Python 3.9+ **stdlib only** (`requirements.txt` lists optional *external* tools, not pip deps).
- `python -m unittest discover tests` — run the suite (80 tests). `pytest` is **not** installed globally (pip is a `uv` shim).
- Type checker is **pyright** (run `npx pyright`), configured by `pyrightconfig.json` (standard mode, `scripts` on `extraPaths`, deprecated-alias + missing-type-arg noise off). Clean baseline: 0 errors / 0 warnings — keep it that way.
- Optional external tools: `search-cli` (Homebrew, primary search provider), `weasyprint` (HTML→PDF, needs system libs).

## Architecture Overview

This is a Claude Code **skill** (`SKILL.md` + `reference/*.md` + `scripts/`). The **model** orchestrates by following `reference/methodology.md`; the Python in `scripts/` is a persistence + post-hoc validation layer (stdlib argparse CLIs), **not** an orchestrator.

Data model (v3.0): append-only JSONL with stable `sha256(...)[:16]` IDs — `sources.jsonl` → `evidence.jsonl` → `claims.jsonl`, tied by `run_manifest.json`. Intended pipeline: `citation_manager init-run` → `register-source` → `assign-display-numbers` → model drafts report → `extract_claims` → `verify_claim_support`. Schemas in `schemas/` are **not** enforced at runtime.

## Conventions & Patterns

- **Stdlib only** — do not add third-party Python dependencies.
- Run state is **append-only JSONL** keyed by stable `sha256` IDs; don't mutate in place (the one exception is `verify_claim_support`'s rewrite).
- Scripts expose **argparse subcommands** and emit JSON to stdout.
- Citation numbers `[N]` are render-time only; provenance is the stable `source_id`.
