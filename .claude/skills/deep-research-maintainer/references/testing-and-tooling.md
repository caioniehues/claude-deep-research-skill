# Testing, types, and tooling

## Running tests

```bash
python -m unittest discover tests      # the whole suite (currently 80 tests)
python -m unittest tests.test_validate_report -v   # one module
```

`pytest` is **not** available (the local `pip` is a `uv` shim). Use stdlib `unittest` only.

### Two test patterns — pick by whether the code touches the network

1. **Subprocess (default).** Run the CLI as a child process and parse stdout. This is the house pattern; mirror it for
   new scripts. Type the JSON-parsing helper as `-> Any` (it returns parsed JSON of varying shape):

   ```python
   def run_cm(*args: str) -> Any:
       result = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)
       if result.returncode != 0:
           raise RuntimeError(f'Exit {result.returncode}: {result.stderr}')
       return json.loads(result.stdout) if result.stdout.strip().startswith(('{', '[')) else result.stdout
   ```

2. **Import (for network-touching code).** Some scripts make HTTP calls (`verify_citations` DOI/URL,
   `evidence`/source fetches). Don't hit the network in tests. Put `scripts/` on the path and import the pure functions:

   ```python
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
   import verify_citations  # noqa: E402
   ```
   Test parsing/heuristics/scoring directly; cover the no-network edge cases (e.g. `verify_url('')`).

Reusable fixtures live in `tests/fixtures/` (`valid_report.md` has 10 sources + all sections; `invalid_report.md`
fails several checks). For gate tests, generate self-consistent reports in a `tempfile.TemporaryDirectory()` so the
*only* variable is the thing under test (see `test_validate_report.make_report`).

## Type checking

Type checker is **regular pyright** (run `npx pyright`), configured by `pyrightconfig.json`:

- `typeCheckingMode: "standard"` — strict mode's "unknown type" noise is not worth it for stdlib-only scripts.
- `extraPaths: ["scripts"]` — so the cross-script import (`verify_claim_support` → `citation_manager`) and the test
  imports resolve.
- `reportDeprecated` / `reportMissingTypeArgument` off — the `typing.Dict`/`List` deprecation and missing-type-arg
  warnings are pure noise here.

**Keep the baseline at 0 errors / 0 warnings.** (It was 134 errors + 886 warnings under basedpyright's strict defaults
before the config landed.) If you switch back to `basedpyright`, expect extra rules (`reportAny`, `reportExplicitAny`,
`reportImplicitRelativeImport`, `reportUnannotatedClassAttribute`) that the current config doesn't list.

## Git / repo gotchas

- **`.gitignore` has a broad `*.json` rule** (with `!schemas/*.json`). New config JSON is excluded by default —
  `pyrightconfig.json` had to be `git add -f`'d, and `package.json` is likewise ignored unless you add a `!` exception.
  Watch for this whenever you add a tracked `.json`.
- **No git user identity is set in this repo.** Commit with inline overrides — do **not** modify git config:
  ```bash
  git -c user.name="Caio Niehues" -c user.email="cniehues1@gmail.com" commit -m "..."
  ```
- **`node_modules/`** is ignored (added when eslint was installed locally).
- **Stage specific files by name** rather than `git add -A`; `AGENTS.md` and `.claude/settings.json` are untracked and
  intentionally left out.

## Beads (issue tracking)

This project tracks work in **beads** (`bd`), not TodoWrite/markdown. `bd ready` for available work, `bd show <id>`,
`bd update <id> --claim`, `bd close <id> --reason="..."`. Issues live in a local Dolt DB and sync via `refs/dolt/data`;
`.beads/issues.jsonl` is a passive export and `.beads/` is gitignored. Don't create beads issues for trivial meta-tasks.

## Known test gaps (good first follow-ups)

- `verify_citations.verify_url`'s HEAD→GET / 403 fallback has **no** automated test (needs network or mocking; only the
  empty-URL branch is covered).
- `md_to_html` output is **not** tested end-to-end against `verify_html` — the `verify_html` test uses hand-crafted HTML,
  so it doesn't confirm the McKinsey-template class names actually satisfy `verify_html`'s structure checks.
