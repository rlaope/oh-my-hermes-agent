from __future__ import annotations

from typing import Iterable


HARNESS_QUALITY_SCHEMA_VERSION = "harness_quality/v1"
HARNESS_QUALITY_KEYS = (
    "schema_version",
    "harness",
    "quality_tier",
    "quality_bar",
    "evidence_ladder",
    "wrapper_actions",
    "overclaim_guards",
)


def build_harness_quality_contract(
    *,
    harness: str,
    quality_tier: str,
    quality_bar: Iterable[str],
    evidence_ladder: Iterable[str],
    wrapper_actions: Iterable[str],
    overclaim_guards: Iterable[str],
) -> dict[str, object]:
    return {
        "schema_version": HARNESS_QUALITY_SCHEMA_VERSION,
        "harness": harness,
        "quality_tier": quality_tier,
        "quality_bar": list(quality_bar),
        "evidence_ladder": list(evidence_ladder),
        "wrapper_actions": list(wrapper_actions),
        "overclaim_guards": list(overclaim_guards),
    }


def unknown_harness_quality_contract(name: str) -> dict[str, object]:
    return build_harness_quality_contract(
        harness=name,
        quality_tier="unknown",
        quality_bar=("Treat the harness as unrecognized and ask for explicit operator review before dispatch.",),
        evidence_ladder=("harness_unrecognized", "operator_review_required"),
        wrapper_actions=("show_status",),
        overclaim_guards=("Unknown harness; do not infer runtime capability.",),
    )


def with_wrapper_actions(contract: dict[str, object], allowed_actions: Iterable[str]) -> dict[str, object]:
    allowed = tuple(allowed_actions)
    existing = contract.get("wrapper_actions", [])
    existing_actions = tuple(action for action in existing if isinstance(action, str)) if isinstance(existing, list) else ()
    actions = [action for action in existing_actions if action in allowed]
    if not actions:
        actions = ["show_status"]
    adjusted = dict(contract)
    adjusted["wrapper_actions"] = actions
    return adjusted
