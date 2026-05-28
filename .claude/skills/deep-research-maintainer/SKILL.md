---
name: deep-research-maintainer
description: >-
  Engineering guide for working ON the claude-deep-research-skill codebase itself (NOT for running research).
  Use this whenever you edit or add anything under scripts/ (citation_manager, evidence_store, extract_claims,
  verify_claim_support, validate_report, verify_citations, source_evaluator, md_to_html, verify_html), touch the
  v3.0 append-only evidence/claim pipeline, change citation numbering or the claim-support/validation gates,
  edit the reference/*.md methodology, modify schemas/, or add tests. Consult it BEFORE changing the verification
  pipeline, citation numbering, validation gates, or adding a script, because several non-obvious invariants are
  load-bearing and easy to break silently. If you are about to touch this repo's Python or reference docs, read this first.
---

# Deep Research Skill — maintainer guide

This skill is for **building and maintaining** `claude-deep-research-skill`. It is not the research workflow itself
(that's the repo's own `SKILL.md`). The goal here is to keep you from silently breaking the v3.0 auditability
guarantees while you work.

## Mental model: who does what

The repo is a Claude Code **skill**, not an application. The split is the whole design:

- **The model orchestrates.** Retrieval, triangulation, synthesis, and report prose are done by Claude following
  `reference/methodology.md`. There is **no Python orchestrator** — a previous scaffold (`research_engine.py`) that
  pretended to be one was deleted precisely because it was unwired and misleading. Do not reintroduce an orchestrator.
- **The scripts are a persistence + post-hoc validation substrate.** They give the model the things a language model is
  unreliable at: stable identity, an append-only evidence trail, a typed claim ledger, and deterministic gates. They are
  small stdlib-only `argparse` CLIs that emit JSON to stdout.

Keeping this boundary clear is the single most important thing. When tempted to make a script "smart" or "drive" the
flow, stop — that responsibility belongs to the model + `methodology.md`.

## The v3.0 data model

Append-only JSONL with stable `sha256(...)[:16]` IDs, tied together by a run manifest:

```
run_manifest.json
   └─ sources.jsonl   (source_id  = sha256(canonical_locator))   ← citation_manager register-source
        └─ evidence.jsonl (evidence_id = sha256(source_id+quote+locator)) ← evidence_store add
             └─ claims.jsonl (claim_id = sha256(section_id+text)) ← extract_claims / verify_claim_support
```

Identity is content-addressed so it survives edits, renumbering, and continuation. **Display numbers `[N]` are
render-time only and never stored** — provenance is always the stable `source_id`.

See `references/pipeline.md` for the full per-script walkthrough and the exact command sequence.

## Load-bearing invariants (don't break these without reading the "why")

These are the things that look harmless to change but quietly corrupt the guarantees. The reasoning matters more than
the rule — if you understand the why, you'll handle the edge cases correctly.

1. **One numbering authority.** All `[N]` numbering goes through `citation_manager.build_display_map(sources)`
   (dedup by `source_id`, contiguous from 1). `assign-display-numbers`, `export-bibliography`, and
   `verify_claim_support` all call it (the verifier imports it cross-script via `sys.path`). *Why:* three sites used to
   derive numbering independently and drifted whenever a duplicate source appeared. Never re-derive `[N]` inline — extend
   the helper instead.

2. **The verification ordering is load-bearing:** register **all** sources → `assign-display-numbers` → draft using
   exactly that map → `extract_claims extract` → `verify_claim_support verify --strict`. *Why:* `[N]` *is* a source's
   position in `sources.jsonl`. Drafting `[5]` and only then registering a different 5th source silently corrupts the
   citation — and because the store is append-only, that's detectable but not fixable without re-drafting. If you change
   how numbering or registration works, preserve this ordering and the docs that pin it (`reference/methodology.md` →
   "Verification Leg", `report-assembly.md`, `quality-gates.md`, `SKILL.md`).

3. **`extract_claims add` contract hole.** The manual `add` subcommand does **not** write `_citation_numbers`, so the
   verifier's auto-linker can't resolve its citations. *Why:* linking is deferred to `verify`, which only reads
   `_citation_numbers`. Anything that adds claims via `add` must pass `cited_source_ids` explicitly. If you "fix" this,
   fix it in `add`, not by special-casing the verifier.

4. **`--strict` gate semantics.** `verify_claim_support verify --strict` fails factual claims that are `unsupported`
   (no links) **or** `needs_review` (linked but overlap score < 0.35) — not just zero-link claims. *Why:* without the
   `needs_review` check the gate only catches *missing* links, so any factual claim linked to any evidence row passes
   regardless of relevance.

5. **The source floor is tiered by design** (`validate_report`): `<5` = error (non-zero exit), `5–9` = warning,
   `≥10` = pass. *Why:* this mirrors `quality-gates.md`'s own graceful-degradation band ("<5 → stop", "5–10 → note in
   limitations"). Do **not** "simplify" it to a flat `<10` error — that would contradict the file the check enforces.

6. **Stdlib only.** No third-party Python dependencies, ever. *Why:* the skill must run anywhere with a bare Python.
   This forecloses things like `jsonschema` — which is why `schemas/` is **documentation only** (`schemas/README.md`),
   never validated at runtime. Field shape is enforced in code (required-field checks, `enum` membership, ID patterns).

7. **Append-only state.** Never mutate JSONL rows in place. The one sanctioned exception is `verify_claim_support`
   rewriting `claims.jsonl` to set `support_status`. *Why:* append-only is what makes corruption detectable and the
   trail auditable across compaction/continuation.

8. **Scripts expose argparse subcommands and print JSON to stdout.** Match this when adding a script — it's the contract
   the model and the tests rely on.

## Common tasks

- **Adding a new pipeline script:** stdlib-only, `argparse` subcommands, JSON to stdout, append-only writes with a
  stable `sha256(...)[:16]` ID. Add it to the README architecture list, mention it in `SKILL.md`'s Scripts section, and
  back it with tests. If it produces or consumes `[N]`, route through `build_display_map`.
- **Modifying a gate (validate_report / verify_citations / verify_claim_support):** gates communicate via **exit code**
  (non-zero = fail). Keep that. Re-read the relevant `reference/*.md` first — gate thresholds are documented there and
  the docs are the source of truth (see invariant #5).
- **Changing citation numbering:** edit `build_display_map` only; the three call sites should not diverge. Add a test
  that exercises a duplicate `source_id` to prove they stay in sync.
- **Editing reference docs:** `reference/methodology.md`, `report-assembly.md`, `quality-gates.md`, and the repo
  `SKILL.md` must stay mutually consistent (phase count, check count, source floor, the verification ordering). When you
  change behavior in a script, update the doc that describes it in the same change.
- **Writing tests / type-checking / committing:** see `references/testing-and-tooling.md`.

## Where to look next

- `references/pipeline.md` — the 9 scripts, their CLIs, the exact verification sequence, and the data flow. Read before
  touching the pipeline.
- `references/testing-and-tooling.md` — the `unittest` patterns (subprocess vs. import), `pyright` config, the
  `.gitignore`/git-identity/beads gotchas, and the current known test gaps. Read before writing tests or committing.

Also note: the repo's `CLAUDE.md` carries an always-loaded summary of these same invariants — this skill is the deeper,
task-oriented version. If you update an invariant here, update `CLAUDE.md` too so they don't drift.
