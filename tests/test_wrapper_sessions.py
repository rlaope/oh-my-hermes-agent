from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _local_package import load_local_package

load_local_package()
from omh.paths import resolve_paths
from omh.runtime_artifacts import create_run, export_runtime, validate_runtime
from omh.runtime_records import validate_wrapper_session_record
from omh.wrapper_sessions import (
    WrapperSessionError,
    build_wrapper_session_status,
    create_or_resume_wrapper_session,
    prepare_wrapper_session_handoff,
    record_plan_decision,
    session_id_for_thread_key,
    write_wrapper_session,
)


class WrapperSessionTests(unittest.TestCase):
    def test_session_start_is_metadata_only_and_resumable(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            message = "risky refactor with private-token-123"

            first = create_or_resume_wrapper_session(
                paths,
                message,
                source="discord",
                source_metadata={"source_event_id": "m1", "channel_ref": "c1", "raw": "drop-me"},
            )
            second = create_or_resume_wrapper_session(
                paths,
                message,
                source="discord",
                source_metadata={"source_event_id": "m1", "channel_ref": "c1"},
            )

            session = first["session"]
            self.assertFalse(first["resumed"])
            self.assertTrue(second["resumed"])
            self.assertEqual(session["session_id"], second["session"]["session_id"])
            self.assertEqual(session["session_id"], session_id_for_thread_key("discord:c1:m1"))
            self.assertEqual(session["status"], "plan_presented")
            self.assertEqual(session["decision"], "none")
            self.assertEqual(session["current_run_id"], "")
            self.assertEqual(session["source_metadata"], {"source_event_id": "m1", "channel_ref": "c1"})
            self.assertNotIn(message, json.dumps(first))
            self.assertEqual(validate_wrapper_session_record(session), [])

    def test_plan_acceptance_gates_handoff_and_links_run_ledger(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            message = "risky refactor with private-token-123"
            started = create_or_resume_wrapper_session(
                paths,
                message,
                source="discord",
                source_metadata={"source_event_id": "m1", "channel_ref": "c1"},
            )
            session_id = str(started["session"]["session_id"])

            with self.assertRaises(WrapperSessionError):
                prepare_wrapper_session_handoff(paths, session_id, message)

            accepted = record_plan_decision(paths, session_id, "accept")
            self.assertEqual(accepted["session"]["status"], "plan_accepted")
            self.assertEqual(accepted["status"]["chat_response"]["state"]["next_action"], "prepare_handoff")

            handoff = prepare_wrapper_session_handoff(paths, session_id, message)

            session = handoff["session"]
            self.assertEqual(session["status"], "handoff_prepared")
            self.assertTrue(session["current_run_id"])
            self.assertEqual(handoff["status"]["runtime_status"]["next_action"], "dispatch_to_executor")
            self.assertEqual(handoff["status"]["chat_response"]["state"]["next_action"], "dispatch_to_executor")
            self.assertFalse(handoff["status"]["runtime_status"]["execution"]["observed"])
            self.assertTrue(validate_runtime(paths)["ok"])
            session_path = paths.runtime_wrapper_sessions_dir / session_id / "session.json"
            self.assertNotIn(message, session_path.read_text(encoding="utf-8"))

    def test_revision_and_cancel_do_not_create_run_evidence(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="slack")
            session_id = str(started["session"]["session_id"])

            revised = record_plan_decision(paths, session_id, "revise")
            cancelled = record_plan_decision(paths, session_id, "cancel")

            self.assertEqual(revised["session"]["current_run_id"], "")
            self.assertEqual(cancelled["session"]["status"], "cancelled")
            self.assertEqual(cancelled["status"]["claim_boundary"], "Wrapper session state is not execution evidence.")
            self.assertEqual(validate_runtime(paths)["runs"], [])

    def test_invalid_plan_decision_transitions_are_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="discord")
            session_id = str(started["session"]["session_id"])

            record_plan_decision(paths, session_id, "revise")

            with self.assertRaises(WrapperSessionError):
                record_plan_decision(paths, session_id, "accept")
            with self.assertRaises(WrapperSessionError):
                prepare_wrapper_session_handoff(paths, session_id, "risky refactor")

            cancelled = record_plan_decision(paths, session_id, "cancel")
            self.assertEqual(cancelled["session"]["status"], "cancelled")
            with self.assertRaises(WrapperSessionError):
                record_plan_decision(paths, session_id, "accept")

    def test_clarifying_session_cannot_be_accepted_without_a_plan(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "zzzzunknownphrase", source="discord")
            session_id = str(started["session"]["session_id"])

            self.assertEqual(started["session"]["status"], "clarifying")
            with self.assertRaises(WrapperSessionError):
                record_plan_decision(paths, session_id, "accept")

    def test_handoff_preparation_is_idempotent_and_cannot_be_cancelled(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="discord")
            session_id = str(started["session"]["session_id"])
            record_plan_decision(paths, session_id, "accept")
            first = prepare_wrapper_session_handoff(paths, session_id, "risky refactor")
            second = prepare_wrapper_session_handoff(paths, session_id, "risky refactor")

            self.assertEqual(first["session"]["current_run_id"], second["session"]["current_run_id"])
            with self.assertRaises(WrapperSessionError):
                record_plan_decision(paths, session_id, "cancel")
            status = build_wrapper_session_status(paths, session_id)
            self.assertEqual(status["session_status"], "handoff_prepared")
            self.assertEqual(status["runtime_status"]["next_action"], "dispatch_to_executor")

    def test_status_uses_linked_run_instead_of_session_execution_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="discord")
            session_id = str(started["session"]["session_id"])
            record_plan_decision(paths, session_id, "accept")
            prepare_wrapper_session_handoff(paths, session_id, "risky refactor")

            status = build_wrapper_session_status(paths, session_id)

            self.assertIn("runtime_status", status)
            self.assertNotIn("execution", status)
            self.assertEqual(status["claim_boundary"], "Execution claims come from the linked runtime run ledger, not the wrapper session.")

    def test_export_runtime_includes_wrapper_sessions_without_raw_prompt(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            message = "risky refactor with private-token-123"
            started = create_or_resume_wrapper_session(paths, message, source="discord")
            session_id = str(started["session"]["session_id"])
            record_plan_decision(paths, session_id, "accept")

            exported = export_runtime(paths, redacted=True)

            self.assertTrue(exported["redacted"])
            self.assertEqual(len(exported["wrapper_sessions"]), 1)
            self.assertNotIn(message, json.dumps(exported))

    def test_runtime_validation_rejects_wrong_linked_run_type(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="discord")
            session = dict(started["session"])
            run = create_run(paths, {"skill": "plan", "harness": "planning", "trigger": "test"})
            session.update({"status": "handoff_prepared", "decision": "plan_accepted", "current_run_id": run["run_id"]})
            write_wrapper_session(paths, session)

            validation = validate_runtime(paths)

            self.assertFalse(validation["ok"])
            errors = "\n".join(validation["wrapper_sessions"][0]["errors"])
            self.assertIn("prepared coding delegation run", errors)

    def test_wrapper_session_validator_rejects_authority_drift(self) -> None:
        with TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp) / ".omh", Path(tmp) / ".hermes")
            started = create_or_resume_wrapper_session(paths, "risky refactor", source="discord")
            session = dict(started["session"])
            session["authority"] = {**session["authority"], "session_owns": ["chat_continuity", "plan_decision"]}

            errors = validate_wrapper_session_record(session)

            self.assertIn("wrapper_session authority.session_owns must match the wrapper session authority contract", errors)

    def test_src_does_not_add_network_or_platform_sdk_imports(self) -> None:
        banned = (
            "import requests",
            "import httpx",
            "import openai",
            "import discord",
            "import slack_sdk",
            "from requests",
            "from httpx",
            "from openai",
            "from discord",
            "from slack_sdk",
        )
        source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path("src").rglob("*.py")))

        for needle in banned:
            with self.subTest(needle=needle):
                self.assertNotIn(needle, source)


if __name__ == "__main__":
    unittest.main()
