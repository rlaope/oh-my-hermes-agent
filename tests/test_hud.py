from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from _cli_harness import run_cli


class HudCliTests(unittest.TestCase):
    def test_hud_prints_compact_line_without_runtime_state(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            status, stdout, stderr = run_cli(
                ["--omh-home", str(root / ".omh"), "--hermes-home", str(root / ".hermes"), "hud"],
                output_json=False,
            )

            self.assertEqual(stderr, "")
            self.assertEqual(status, 0)
            self.assertIn("[omh] v1.0.0", stdout)
            self.assertIn("tokens:unobserved", stdout)
            self.assertIn("plugin:missing", stdout)

    def test_hud_reports_setup_plugin_target_and_prepared_runtime_boundary(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            omh_home = root / ".omh"
            hermes_home = root / ".hermes"
            self.assertEqual(run_cli(["--omh-home", str(omh_home), "--hermes-home", str(hermes_home), "setup"])[0], 0)
            status, stdout, stderr = run_cli(
                [
                    "--omh-home",
                    str(omh_home),
                    "--hermes-home",
                    str(hermes_home),
                    "coding",
                    "delegate",
                    "--record",
                    "--executor",
                    "codex",
                    "Safely add feature without overclaiming.",
                ]
            )
            self.assertEqual(stderr, "")
            self.assertEqual(status, 0)
            run_id = json.loads(stdout)["runtime"]["run"]["run_id"]

            status, stdout, stderr = run_cli(
                [
                    "--omh-home",
                    str(omh_home),
                    "--hermes-home",
                    str(hermes_home),
                    "hud",
                    "--json",
                    "--preset",
                    "full",
                    "--tokens-remaining",
                    "1200",
                    "--token-budget",
                    "4000",
                ]
            )

            self.assertEqual(stderr, "")
            self.assertEqual(status, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["schema_version"], "omh_hud/v1")
            self.assertEqual(payload["version"], "1.0.0")
            self.assertEqual(payload["plugin"]["status"], "ready")
            self.assertEqual(payload["target_topology"]["mode"], "single_agent_target")
            self.assertEqual(payload["runtime"]["latest_run_id"], run_id)
            self.assertEqual(payload["runtime"]["evidence_state"], "prepared_not_observed")
            self.assertEqual(payload["tokens"]["status"], "observed_from_host_metadata")
            self.assertIn("tokens:1200/4000", payload["display"]["line"])
            self.assertIn("evidence:prepared_not_observed", payload["display"]["line"])
            self.assertIn("Prepared handoffs are not execution", payload["evidence_boundary"])


if __name__ == "__main__":
    unittest.main()
