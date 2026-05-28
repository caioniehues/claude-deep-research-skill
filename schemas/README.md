# Schemas — descriptive, not enforced

These JSON Schema files document the shape of the v3.0 append-only artifacts:

| File | Describes |
|------|-----------|
| `source.schema.json` | rows in `sources.jsonl` (written by `citation_manager.py register-source`) |
| `evidence.schema.json` | rows in `evidence.jsonl` (written by `evidence_store.py add`) |
| `claim.schema.json` | rows in `claims.jsonl` (written by `extract_claims.py` and `verify_claim_support.py`) |
| `run_manifest.schema.json` | `run_manifest.json` (written by `citation_manager.py init-run`) |

**They are documentation only — nothing validates against them at runtime.** The
scripts are stdlib-only by design (see the project `CLAUDE.md`), and `jsonschema`
is a third-party dependency we deliberately do not add. Field shape is enforced
in code (required-field checks, `enum` membership, stable-ID patterns) inside the
writer scripts, not by loading these files.

If you change a writer script's output, update the matching schema here so the
documentation stays honest. In particular, `claims.jsonl` rows carry three
internal `_`-prefixed fields (`_citation_numbers`, `_support_score`,
`_support_notes`) that are documented in `claim.schema.json`; keep that list in
sync with `extract_claims.py` / `verify_claim_support.py`.
