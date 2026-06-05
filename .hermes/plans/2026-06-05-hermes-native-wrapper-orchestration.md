---
schema_version: hermes_plan/v1
status: approved
source: ralplan
review_gate:
  architect: approved
  critic: approved
---

# Hermes-Native Wrapper Orchestration Plan

## Intent

OMHM should reach OMX-like product weight without copying OMX. The product
direction is not to clone OMX runtime/team internals. OMHM should become the
deterministic Hermes-native wrapper orchestration layer for chat agents:
Discord, Slack, or hosted Hermes wrappers receive natural-language messages,
turn them into skill/plan/status/handoff UX, and delegate coding-shaped work to
Codex-like executors.

## Decision

Build a wrapper session decision/index contract first. Do not start with real
Discord/Slack SDKs, Hermes core patches, LLM/API calls, network calls, or direct
Codex process spawning.

## Principles

- Hermes-native UX: users talk to Hermes in chat, not to CLI command recipes.
- Deterministic core: OMHM composes schemas, local artifacts, and CLI contracts.
- Delegation honesty: prepared, dispatched, executed, reviewed, CI-passed, and
  merged are separate observable states.
- Transport portability: Discord, Slack, and hosted Hermes wrappers consume the
  same platform-neutral contract.
- Codex-first coding: implementation-heavy work is handed off to Codex-like
  executors.

## Authority Model

- `thread_key`: platform continuity key from `chat_interaction/v1`.
- `session_id`: deterministic local wrapper-session id derived from
  `thread_key`, for example `ws-<sha256(thread_key)>`.
- `run_id`: existing `.omh/runtime/runs/<run-id>` evidence id. It appears only
  after a workflow run or prepared coding handoff exists.

Wrapper sessions own chat continuity, route summary, plan presentation, plan
accepted/revision/cancelled decisions, and links to plan artifacts or run ids.
Existing runtime runs own prepared handoff, dispatch, executor result,
verification, review, CI, merge readiness, and merge observations.

The key invariant: session state must never become execution evidence.

## Milestones

### Milestone 1: Wrapper Session Contract

Add a metadata-only wrapper session layer that can start/resume a session,
record plan accepted/revision/cancelled decisions, link to a prepared coding
run, derive next action from current evidence, render chat status, and
participate in runtime validation/export.

### Milestone 2: Coding Evidence Expansion

Make review, CI, merge readiness, and merge observed first-class run-level
evidence records instead of generic wrapper gaps.

### Milestone 3: Adapter Reference Contract

Add Discord/Slack example fixtures and pseudocode showing how adapters call
OMHM, map actions to buttons, update threads, and recover after process restart.

### Milestone 4: Optional Executor Bridge

Only after the contract is stable, decide whether OMHM should start Codex
sessions itself or remain a handoff provider for external wrappers.

### Milestone 5: Operational Depth

Expand doctor/probe/status to validate wrapper session directories, adapter
fixture compatibility, executor evidence integrity, and stale in-flight runs.

## First PR Vertical Slice

Title: Wrapper session lifecycle contract.

Implement a deterministic local wrapper session layer:

- New module, likely `src/wrapper_sessions.py`.
- Store metadata-only state under `.omh/runtime/wrapper_sessions/<session-id>/`.
- Add schema records for session started/resumed, plan presented, plan accepted,
  plan revision requested, plan cancelled, handoff prepared, and status
  rendered.
- Link sessions to `current_run_id` when a coding handoff is prepared.
- Keep execution evidence in existing `.omh/runtime/runs/<run-id>/`.
- Add CLI surface under `omh chat` or `omh runtime` for adapter authors and
  tests.
- Add runtime validation/export coverage for wrapper sessions.
- Update README and architecture docs conservatively.

## Acceptance Criteria

- A wrapper can create or resume a session from source metadata and receive the
  same stable `thread_key` and `session_id`.
- Plan acceptance is persisted before `prepare_handoff` becomes enabled.
- Handoff preparation creates or links an existing run id, but remains
  `prepared_not_observed`.
- Session status reads linked run evidence and never duplicates execution
  claims.
- Review, CI, merge readiness, and merge remain not observed in the first PR
  unless future run-level evidence records exist.
- Status copy is chat-native and does not tell end users to run `omh` commands.
- Runtime validation and redacted export include wrapper session records.
- All new behavior is deterministic and local-only.

## Test Plan

- Unit tests for session identity, metadata filtering, plan decision gates,
  handoff gates, status derivation, and privacy.
- CLI tests with temporary `--omh-home` and `--hermes-home` directories.
- Restart-style test: create session, record plan acceptance, reload from disk,
  and render the correct next status.
- Linked-run test: prepared coding run exists, session links to it, and status
  delegates execution claims to the existing runtime summary.
- Static/local guard test that the first PR does not introduce Discord/Slack SDK
  imports, network clients, or LLM/API calls.

Minimum verification commands:

```sh
PYTHONPATH=tests uv run python -m unittest tests/test_cli.py -v
PYTHONPATH=tests uv run python -m unittest tests/test_wrapper_contract.py -v
PYTHONPATH=tests uv run python -m unittest tests/test_coding_lifecycle.py -v
PYTHONPATH=tests uv run python -m unittest tests/test_runtime_artifacts.py -v
```

Broader verification:

```sh
PYTHONPATH=tests uv run python -m unittest discover tests -v
uv run omh doctor
uv run omh chat interact --source discord "risky refactor"
```

## ADR

Decision: choose wrapper session decision/index first.

Drivers:

- The primary product surface is chat.
- The largest current gap is lifecycle continuity between wrapper actions, plan
  acceptance, coding handoff, and observed completion evidence.
- The first PR must remain deterministic, local-only, and testable.

Rejected:

- Full adapters first, because SDK/network/auth choices would dominate the PR.
- Direct Codex spawning first, because process/session orchestration is too
  large before the wrapper contract is stable.
- OMX runtime clone, because OMHM should stay Hermes-native.
- Single unified store, because it would overload execution runs with chat
  session concerns.

Consequences:

- Adapters remain external for now.
- OMHM gains a stronger core contract that future adapters and executor bridges
  can share.
- Existing run records remain canonical for execution evidence.

## Execution Handoff

Recommended next lane:

```text
[$ultragoal] .hermes/plans/2026-06-05-hermes-native-wrapper-orchestration.md
```

For parallel implementation after goal setup, use `$team` with lanes for
session module, CLI/tests, and docs. Use `$ralph` only as an explicit
single-owner fallback.

## Stop Condition

The first PR is complete when a wrapper can persist plan acceptance, prepare a
Codex handoff only after acceptance, link that handoff to the existing run
ledger, recover status after restart, and prove via tests that no
execution/review/CI/merge claim is made from session state alone.
