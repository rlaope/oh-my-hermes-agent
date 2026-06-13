# OMH Role Surface

OMH roles are responsibility descriptors, not runtime agents. They make chat responses, wrapper buttons, and status cards easier to read without claiming that a separate worker exists or ran.

Use roles inside the flagship `request-to-handoff` path:

`plain request -> responsible role -> plan/status/handoff action -> observed evidence boundary`

## Operating Models

Operating models are lighter than role profile packs. They record the default
Hermes collaboration posture selected during setup, but they do not install
role files or claim that separate agents ran.

| ID | Default posture |
| --- | --- |
| `solo-operator` | Keep the safest single-operator defaults and ask before executor dispatch. |
| `small-team` | Bias chat narration toward product, technical, QA, and release ownership without installing team files. |
| `research-ops` | Keep Hermes focused on research, strategy, and meeting workflows. |
| `coding-runtime-team` | Make selected Hermes/OMX/OMO/OMC runtime handoffs and observed runtime ladder status first-class. |

Use `omh setup --operating-model <id>` for these defaults. Use
`omh setup --profile-pack <id>` only when you also want visible role files under
Hermes.

## Roles

### Research Lead

- ID: `research-lead`
- Purpose: Own source-backed discovery and keep evidence, inference, confidence, and unknowns separate.
- Owns:
  - Research question and source boundary
  - Observed evidence versus inferred trend
  - Research summary that can feed planning or strategy
- Primary skills: `web-research`, `best-practice-research`, `research-brief`, `autoresearch-goal`
- Primary harnesses: `research`, `business-research`
- Wrapper actions: `ask_followup`, `show_sources`, `show_status`
- Evidence boundary: A research role can prepare or summarize evidence; it is not implementation, review, CI, or merge evidence.

### Planning Lead

- ID: `planning-lead`
- Purpose: Own clarification, non-goals, acceptance criteria, tradeoffs, and verification strategy.
- Owns:
  - One-question clarification when scope is ambiguous
  - Plan artifact with goals, non-goals, risks, and verification
  - Decision gate before handoff or execution
- Primary skills: `deep-interview`, `plan`, `ralplan`, `strategy-brief`
- Primary harnesses: `deep-interview`, `planning`, `strategy-synthesis`
- Wrapper actions: `ask_followup`, `accept_plan`, `revise_plan`, `show_status`
- Evidence boundary: A planning role can make work reviewable; it is not proof that the work was accepted or executed.

### Review Gate

- ID: `review-gate`
- Purpose: Own claim checking, release/readiness review, QA framing, and evidence requirements.
- Owns:
  - Findings and risks
  - Verification, CI, and release-readiness status
  - Follow-up handoff only when fixes are accepted
- Primary skills: `code-review`, `ultraqa`, `ops-review`
- Primary harnesses: `code-review`, `qa`, `ops-review`
- Wrapper actions: `show_findings`, `prepare_fix_handoff`, `refresh_status`
- Evidence boundary: Review findings are not fix evidence; merge-ready is not merged.

### Coding Handoff

- ID: `coding-handoff`
- Purpose: Own executor/runtime selection, prepared handoff payloads, and status narration while the chosen coding agent or runtime owns code changes.
- Owns:
  - Executor, runtime, or Hermes coding-skill choice
  - Prepared coding handoff with team/swarm, worker, worktree, acceptance, and verification expectations when relevant
  - Observed lifecycle status when a tested executor contract records it
- Primary skills: `ultragoal`, `ultrawork`, `ralph`, `ai-slop-cleaner`
- Primary harnesses: `goal-execution`, `parallel-delivery`, `coding-handling`
- Wrapper actions: `choose_executor`, `show_prompt_handoff`, `show_runtime_handoff`, `start_team`, `start_swarm`, `prepare_worktree`, `send_to_executor`, `show_status`
- Evidence boundary: A prepared coding handoff is not executor/runtime dispatch, worker start, worktree creation, result, verification, review, CI, merge readiness, or merge evidence. Hermes/OMX/OMO/OMC runtime handoffs must record separate `runtime_observation/v1` events before the status can move from prepared to observed.

## Public Claim Rule

A role can explain responsibility and next action. A role does not prove execution, dispatch, review, CI, merge readiness, or merge evidence. Those claims require matching observed runtime or wrapper evidence.
