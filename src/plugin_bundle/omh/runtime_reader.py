from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STATUS_SCHEMA_VERSION = "omh_status/v1"
HUD_SCHEMA_VERSION = "omh_hud/v1"
HUD_PRESETS = {"minimal", "focused", "full"}


def _expand_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser().resolve()


def _default_omh_home() -> Path:
    return _expand_path(os.environ.get("OMH_HOME", "~/.omh"))


def _default_hermes_home() -> Path:
    return _expand_path(os.environ.get("HERMES_HOME", "~/.hermes"))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _bool_from_record(record: dict[str, Any], key: str = "observed") -> bool:
    return bool(record.get(key, False)) if record else False


def _summarize_run(run_dir: Path) -> dict[str, Any]:
    run = _read_json(run_dir / "run.json")
    coding = _read_json(run_dir / "coding_delegation.json")
    delegation = _read_json(run_dir / "delegation.json")
    wrapper = _read_json(run_dir / "wrapper.json")
    review = _read_json(run_dir / "review.json")
    ci = _read_json(run_dir / "ci.json")
    merge = _read_json(run_dir / "merge.json")
    return {
        "run_id": str(run.get("run_id", run_dir.name)),
        "workflow": str(coding.get("recommended_workflow") or run.get("skill", "unknown")),
        "harness": str(coding.get("recommended_harness") or run.get("harness", "unknown")),
        "phase": str(run.get("phase", run.get("status", "unknown"))),
        "artifact_kind": str(run.get("artifact_kind", "")),
        "observation_status": str(run.get("observation_status", coding.get("status", "unknown"))),
        "prepared_handoff": bool(coding) and str(coding.get("status", "")) == "prepared_not_observed",
        "prompt_dispatched": _bool_from_record(wrapper, "prompt_dispatched"),
        "execution_observed": _bool_from_record(delegation),
        "verification_observed": _bool_from_record(wrapper, "verification_observed"),
        "review_observed": _bool_from_record(review),
        "review_status": str(review.get("status", "not_observed" if review else "unknown")),
        "ci_observed": _bool_from_record(ci),
        "ci_status": str(ci.get("status", "not_observed" if ci else "unknown")),
        "merge_observed": _bool_from_record(merge),
        "merge_status": str(merge.get("status", "not_observed" if merge else "unknown")),
    }


def read_omh_hud(
    omh_home: str | Path | None = None,
    hermes_home: str | Path | None = None,
    *,
    preset: str = "focused",
    limit: int = 3,
    token_metadata: dict[str, Any] | None = None,
    package_version: str = "",
) -> dict[str, Any]:
    safe_preset = preset if preset in HUD_PRESETS else "focused"
    home = _expand_path(omh_home) if omh_home else _default_omh_home()
    hermes = _expand_path(hermes_home) if hermes_home else _default_hermes_home()
    status = read_omh_status(home, limit=limit)
    state = _read_json(home / "runtime" / "state.json")
    manifest = _read_json(home / "manifest.json")
    profile = _read_json(home / "setup-profile.json")
    target_registry = _read_json(home / "targets.json")
    runs = status.get("runs", [])
    latest_run = runs[0] if runs else {}
    payload: dict[str, Any] = {
        "schema_version": HUD_SCHEMA_VERSION,
        "preset": safe_preset,
        "package": "oh-my-hermes",
        "version": _package_version(state, package_version),
        "omh_home": str(home),
        "hermes_home": str(hermes),
        "skills": _skills_summary(manifest, state),
        "plugin": _plugin_summary(hermes, state),
        "target_topology": _target_topology_summary(target_registry),
        "executor": _executor_summary(profile),
        "runtime": _hud_runtime_summary(status, latest_run),
        "tokens": _token_summary(token_metadata or {}),
        "evidence_boundary": (
            "HUD is metadata-only. Prepared handoffs are not execution, review, CI, merge, or token-usage evidence."
        ),
        "privacy": "metadata_only",
    }
    payload["display"] = {
        "line": format_omh_hud_line(payload, preset=safe_preset),
        "segments": _hud_segments(payload, preset=safe_preset),
    }
    return payload


def format_omh_hud_line(payload: dict[str, Any], *, preset: str = "focused") -> str:
    return " | ".join(_hud_segments(payload, preset=preset))


def _package_version(state: dict[str, Any], fallback: str) -> str:
    value = str(state.get("version", "") or fallback or "").strip()
    if value:
        return value
    last_install = state.get("last_install", {})
    if isinstance(last_install, dict):
        release_update = last_install.get("release_update", {})
        current = release_update.get("current", {}) if isinstance(release_update, dict) else {}
        value = str(current.get("package_version", "") if isinstance(current, dict) else "").strip()
    return value or "unknown"


def _skills_summary(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    skills = manifest.get("skills", [])
    count = len(skills) if isinstance(skills, list) else _safe_int(state.get("installed_skills"), 0)
    return {
        "count": count,
        "status": "installed" if count else "missing",
    }


def _plugin_summary(hermes_home: Path, state: dict[str, Any]) -> dict[str, Any]:
    plugin_dir = hermes_home / "plugins" / "omh"
    installed = plugin_dir.is_dir()
    ready = installed and (plugin_dir / "plugin.yaml").is_file() and (plugin_dir / "__init__.py").is_file()
    last_distribution = state.get("last_plugin_distribution", {})
    observed = bool(last_distribution.get("observed", False)) if isinstance(last_distribution, dict) else False
    if ready:
        status = "ready"
    elif installed or observed:
        status = "installed"
    else:
        status = "missing"
    return {
        "status": status,
        "plugin_dir": str(plugin_dir),
        "distribution_observed": observed,
        "runtime_observed": False,
    }


def _target_topology_summary(registry: dict[str, Any]) -> dict[str, Any]:
    topology = registry.get("topology", {}) if isinstance(registry, dict) else {}
    if not isinstance(topology, dict):
        topology = {}
    targets = registry.get("targets", {}) if isinstance(registry, dict) else {}
    known_count = _safe_int(topology.get("known_target_count"), len(targets) if isinstance(targets, dict) else 0)
    active_count = _safe_int(topology.get("active_agent_count"), known_count)
    mode = str(topology.get("mode", "") or "").strip()
    if not mode:
        mode = "multi_agent_targets" if active_count > 1 else "single_agent_target" if active_count == 1 else "unknown"
    return {
        "mode": mode,
        "known_target_count": known_count,
        "active_agent_count": active_count,
        "transition": str(topology.get("transition", "unknown") or "unknown"),
    }


def _executor_summary(profile: dict[str, Any]) -> dict[str, Any]:
    executor = str(profile.get("default_executor", "") or "").strip() if isinstance(profile, dict) else ""
    if not executor:
        executor = "choose"
    return {
        "default": executor,
        "dispatch_policy": str(profile.get("dispatch_policy", "ask_before_dispatch") if isinstance(profile, dict) else "ask_before_dispatch"),
    }


def _hud_runtime_summary(status: dict[str, Any], latest_run: dict[str, Any]) -> dict[str, Any]:
    runs = status.get("runs", [])
    run_count = len(runs) if isinstance(runs, list) else 0
    if not latest_run:
        return {
            "state_present": bool(status.get("runtime_state_present", False)),
            "recent_run_count": run_count,
            "latest_run_id": "",
            "workflow": "idle",
            "phase": "idle",
            "observation_status": "idle",
            "evidence_state": "idle",
        }
    return {
        "state_present": bool(status.get("runtime_state_present", False)),
        "recent_run_count": run_count,
        "latest_run_id": str(latest_run.get("run_id", "")),
        "workflow": str(latest_run.get("workflow", "unknown")),
        "phase": str(latest_run.get("phase", "unknown")),
        "observation_status": str(latest_run.get("observation_status", "unknown")),
        "evidence_state": _evidence_state(latest_run),
    }


def _evidence_state(run: dict[str, Any]) -> str:
    if run.get("merge_observed"):
        return "merge_observed"
    if run.get("ci_observed"):
        return "ci_observed"
    if run.get("review_observed"):
        return "review_observed"
    if run.get("verification_observed"):
        return "verification_observed"
    if run.get("execution_observed"):
        return "execution_observed"
    if run.get("prompt_dispatched"):
        return "dispatch_observed"
    if run.get("prepared_handoff"):
        return "prepared_not_observed"
    return str(run.get("observation_status", "unknown") or "unknown")


def _token_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    values = {
        key: value
        for key, value in (
            ("tokens_remaining", _optional_number(metadata.get("tokens_remaining"))),
            ("token_budget", _optional_number(metadata.get("token_budget"))),
            ("input_tokens", _optional_number(metadata.get("input_tokens"))),
            ("output_tokens", _optional_number(metadata.get("output_tokens"))),
            ("context_remaining_percent", _optional_number(metadata.get("context_remaining_percent"))),
        )
        if value is not None
    }
    if not values:
        return {
            "status": "unobserved",
            "summary": "unobserved",
            "values": {},
        }
    summary = _token_display(values)
    return {
        "status": "observed_from_host_metadata",
        "summary": summary,
        "values": values,
    }


def _token_display(values: dict[str, int | float]) -> str:
    remaining = values.get("tokens_remaining")
    budget = values.get("token_budget")
    percent = values.get("context_remaining_percent")
    if remaining is not None and budget is not None:
        return f"{remaining}/{budget}"
    if remaining is not None:
        return f"remaining={remaining}"
    if percent is not None:
        return f"context={percent}%"
    parts = []
    if values.get("input_tokens") is not None:
        parts.append(f"in={values['input_tokens']}")
    if values.get("output_tokens") is not None:
        parts.append(f"out={values['output_tokens']}")
    return ",".join(parts) if parts else "observed"


def _hud_segments(payload: dict[str, Any], *, preset: str) -> list[str]:
    version = str(payload.get("version", "unknown"))
    tokens = payload.get("tokens", {})
    plugin = payload.get("plugin", {})
    skills = payload.get("skills", {})
    topology = payload.get("target_topology", {})
    executor = payload.get("executor", {})
    runtime = payload.get("runtime", {})
    base = [f"[omh] v{version}", f"tokens:{tokens.get('summary', 'unobserved')}"]
    if preset == "minimal":
        return [*base, _activity_label(runtime)]
    focused = [
        *base,
        f"plugin:{plugin.get('status', 'unknown')}",
        f"skills:{skills.get('count', 0)}",
        f"target:{_topology_label(topology)}",
        f"executor:{executor.get('default', 'choose')}",
        f"run:{_run_label(runtime)}",
    ]
    if preset == "full":
        focused.append(f"evidence:{runtime.get('evidence_state', 'unknown')}")
    return focused


def _activity_label(runtime: dict[str, Any]) -> str:
    workflow = str(runtime.get("workflow", "idle"))
    phase = str(runtime.get("phase", "idle"))
    return "idle" if workflow == "idle" else f"{workflow}:{phase}"


def _run_label(runtime: dict[str, Any]) -> str:
    run_id = str(runtime.get("latest_run_id", ""))
    if not run_id:
        return "none"
    return f"{_activity_label(runtime)}#{run_id[:8]}"


def _topology_label(topology: dict[str, Any]) -> str:
    mode = str(topology.get("mode", "unknown"))
    active = _safe_int(topology.get("active_agent_count"), 0)
    if mode == "single_agent_target":
        return "single"
    if mode == "multi_agent_targets":
        return f"multi:{active}"
    return "unknown"


def _optional_number(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_omh_status(omh_home: str | Path | None = None, limit: int = 5) -> dict[str, Any]:
    safe_limit = max(0, min(int(limit), 20))
    home = _expand_path(omh_home) if omh_home else _default_omh_home()
    runtime_dir = home / "runtime"
    runs_dir = runtime_dir / "runs"
    state = _read_json(runtime_dir / "state.json")
    runs: list[dict[str, Any]] = []
    if runs_dir.exists():
        for run_json in sorted(runs_dir.glob("*/run.json"), reverse=True)[:safe_limit]:
            runs.append(_summarize_run(run_json.parent))
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "omh_home": str(home),
        "runtime_dir": str(runtime_dir),
        "runtime_state_present": bool(state),
        "latest_run_id": str(state.get("last_run_id", "")) if state else "",
        "runs": runs,
        "evidence_boundary": {
            "prepared_handoff": "not execution evidence",
            "execution": "requires observed delegation result",
            "verification": "requires observed wrapper verification",
            "review": "requires separate review record",
            "ci": "requires separate CI record",
            "merge": "requires separate merge record",
        },
        "privacy": "metadata_only",
    }
