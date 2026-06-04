# Architecture

## Goals

oh-my-hermes-agent should feel like a native Hermes workflow layer, not a pile
of copied prompt files.

The architecture favors:

- a small command interface
- reversible local installation
- generated skill text from testable catalog data
- explicit compatibility contracts
- conservative routing behavior

## Package Layout

```text
src/
  cli.py
  config_adapter.py
  converter.py
  doctor.py
  installer.py
  manifest.py
  paths.py
  snippet.py
  skill_pack.py
  core/
  skills/
```

## Main Modules

`cli.py` owns command parsing and user-facing JSON output.

`installer.py` owns managed skill writes, manifest updates, update behavior, and
uninstall behavior.

`config_adapter.py` owns the Hermes config edit boundary. It should remain
small, heavily tested, and conservative.

`skills/catalog.py` owns workflow names, descriptions, trigger phrases, and
use-when rules as data.

`skills/render.py` owns generated `SKILL.md` content. It should render from the
catalog rather than becoming a second source of truth.

`skill_pack.py` is a compatibility facade so older imports keep working while
the package grows internally.

## Routing

Routing is prompt-level guidance. The router skill gives Hermes a structured map
of workflow names and strong trigger phrases, but it does not override Hermes
core behavior.

Future routing work should deepen the catalog first, then render richer skill
metadata from it.

## Harness Contract

Representative harnesses are preview metadata for generated prompt guidance.
They are not separate runtime roles, hidden hooks, or proof that Hermes exposes a
matching internal role system.

Runtime artifacts make that boundary inspectable. A harness can request local
evidence under `.omh/runtime/`, but the artifact must separate requested
delegation from observed delegation. If Hermes or a wrapper does not expose a
specialist lane result, the recorded result stays `not_observed` or
`not_available`.

When a harness is added, removed, or renamed, update these surfaces together:

- `src/skills/catalog.py`
- `src/skills/render.py`
- `docs/APPLICATION_CASES.md`
- `tests/test_router_content.py`

Each harness must also define runtime evidence expectations in catalog data:

- artifact event names
- delegation expectation
- privacy default

This keeps the generated router, public examples, and regression tests aligned
around one catalog contract.

## Runtime Artifacts

Runtime artifacts are local JSON/JSONL files under `.omh/runtime/`.

```text
.omh/
  runtime/
    state.json
    runs/
      <run-id>/
        run.json
        events.jsonl
        delegation.json
        evidence/
```

`state.json` records install, apply, and doctor summaries. A run directory
records a workflow envelope, append-only events, delegation observation, and
optional evidence files.

The runtime artifact layer is intentionally small:

- JSON/JSONL only
- no external service
- no prompt body capture by default
- schema-versioned files
- CLI inspection through `omh runtime status`, `omh runtime runs`, and
  `omh runtime show <run-id>`

Bot wrappers can call `omh runtime record` before invoking Hermes and
`omh runtime delegate` after the response if delegation metadata is available.
If not, they should record `not_observed` rather than guessing.

## Safety Model

- Managed files are tracked by manifest hashes.
- Local modifications block updates unless `--force` is supplied.
- Config registration is isolated to `skills.external_dirs`.
- Workspace guidance is printed by `omh snippet`; it is not applied by default.
- Runtime artifacts are local metadata by default and do not capture prompt or
  response bodies unless a future explicit opt-in is added.
