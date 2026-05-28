# The v3.0 pipeline — scripts, CLIs, and the verification sequence

All scripts live in `scripts/`, are stdlib-only `argparse` CLIs, and print JSON to stdout. IDs are
`sha256(...)[:16]` hex over a canonical payload.

## Table of contents
- [The canonical run sequence](#the-canonical-run-sequence)
- [Per-script reference](#per-script-reference)
- [The numbering authority](#the-numbering-authority)
- [Claim types and support scoring](#claim-types-and-support-scoring)

## The canonical run sequence

This ordering is load-bearing (see invariant #2 in SKILL.md). The model runs it; the scripts enforce the data shape.

```
1. citation_manager.py init-run --out-dir DIR --query "..." --mode deep
      → run_manifest.json + empty sources/evidence/claims .jsonl
2. citation_manager.py register-source --json '{"raw_url":...,"title":...}' --dir DIR   (for EVERY source, during retrieval)
3. evidence_store.py add --json '{"source_id":...,"quote":...,"evidence_type":...,"locator":...}' --dir DIR
4. citation_manager.py assign-display-numbers --dir DIR        (ONLY after all sources registered → source_id→[N] map)
5. <model drafts report.md using exactly that [N] map>
6. extract_claims.py extract --report report.md --dir DIR      (captures [N] into _citation_numbers; cited_source_ids stays empty)
7. verify_claim_support.py verify --dir DIR --strict           (links [N]→source_id, scores support, gates on exit code)
```

Then the structural/citation validators (independent of the above): `validate_report.py --report` and
`verify_citations.py --report`, and rendering via `md_to_html.py` / `verify_html.py`.

## Per-script reference

### citation_manager.py — identity, manifest, numbering
- `init-run --out-dir --query --mode` — create manifest + empty artifacts.
- `register-source --json --dir` — append a source; `source_id = sha256(canonical_locator)`, where the canonical
  locator prefers DOI, then arXiv, then a normalized URL (lowercased host, fragment + tracking params stripped).
  Re-registering a known source is a no-op (dedup by `source_id`).
- `assign-display-numbers --dir` — print the `source_id → [N]` map via `build_display_map`.
- `export-bibliography --dir --style markdown|json` — render the bibliography; numbers also come from `build_display_map`.
- Home of `build_display_map(sources)` — the single numbering authority.

### evidence_store.py — append-only evidence
- `add --json --dir` — `evidence_id = sha256(source_id + normalized_quote + locator)`; same quote+source dedupes.
- `list --dir [--source-id]`.
- Evidence must be persisted here *before* synthesis so continuation agents and the gate can see the full trail.

### extract_claims.py — typed claim ledger
- `extract --report --dir` — split the report into atomic claims; each gets a `claim_type`
  (`factual` | `synthesis` | `recommendation` | `speculation`). Captures each sentence's `[N]` into
  `_citation_numbers`; leaves `cited_source_ids` empty (linking deferred to the verifier).
- `add --json --dir` — manual single claim. **Does not write `_citation_numbers`** → callers must pass
  `cited_source_ids` explicitly (the contract hole).
- `list` / `stats`.

### verify_claim_support.py — the claim-support gate (deterministic, no LLM)
- `verify --dir [--strict]` — resolve each claim's `[N]` → `source_id` via `build_display_map`, gather linked evidence
  quotes, score support (weighted token / number / year / entity overlap), write `support_status` (this is the one
  sanctioned in-place rewrite of `claims.jsonl`). `--strict` exits non-zero on factual `unsupported` OR `needs_review`.
- `report --dir` — human-readable support summary.

### source_evaluator.py — credibility scoring
- `--json '{"url":...,"title":...,"publication_date":...,"author":...}'` → JSON with `overall_score`,
  `domain_authority`, `recency`, `expertise`, `bias_score`, `recommendation`.

### validate_report.py — 9-check structure gate
- `--report` → exit 0 pass / 1 fail. Checks: exec-summary length, required sections, citation format, bibliography
  integrity, placeholder text, content-truncation, word count, **tiered source floor (<5 err / 5–9 warn / ≥10)**,
  broken internal links.

### verify_citations.py — citation authenticity gate
- `--report [--strict]`. Resolves DOIs, checks URL reachability (browser UA + HEAD→GET fallback on method/client-reject
  codes; treats 2xx/3xx as reachable), and runs hallucination heuristics (future years, anachronistic AI terms,
  templated titles, recent claims with no verification path).

### md_to_html.py — markdown → HTML
- `[report.md] [-o OUT] [--template T] [--fragments-only]`. Substitutes the report into the McKinsey template
  (`{{CONTENT}}`, `{{BIBLIOGRAPHY}}`, `{{TITLE}}`, `{{DATE}}`, `{{SOURCE_COUNT}}`); minimal HTML5 fallback if no
  template. Writes a full `.html` to disk and prints a JSON status.

### verify_html.py — HTML/markdown consistency
- `--html --md`. Confirms sections carried across, no unreplaced `{{placeholders}}`, no emojis, valid structure,
  citations + bibliography present.

## The numbering authority

`build_display_map(sources)` dedups by `source_id` (first occurrence wins) and numbers contiguously from 1 in
registration order. It is the contiguous, reader-facing scheme (what the bibliography shows). The three consumers
(`assign-display-numbers`, `export-bibliography`, `verify_claim_support`) must all use it so a duplicate `source_id`
can never make them disagree. In practice duplicates can't occur (register-source rejects them), so this is a latent
invariant — keep it intact anyway, and test it with a deliberately duplicated row.

## Claim types and support scoring

- `factual` — hard-fails on lack of support under `--strict`.
- `synthesis` / `recommendation` — need traceability, softer threshold.
- `speculation` — labeled, no support gate (treated as supported).

Support thresholds in `compute_support_score`: `≥0.6 → supported`, `≥0.35 → partial`, `<0.35 → needs_review`;
zero links → `unsupported`. `--strict` fails factual `unsupported` + `needs_review`.
