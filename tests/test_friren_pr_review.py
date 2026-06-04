from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


def load_review_module():
    script = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "friren_pr_review.py"
    spec = importlib.util.spec_from_file_location("friren_pr_review", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


review = load_review_module()


class FrirenReviewTests(unittest.TestCase):
    def test_source_change_without_tests_gets_warning_and_footer(self) -> None:
        pr = review.PullRequest(
            number=12,
            title="feat: add router",
            author="rlaope",
            draft=False,
            additions=42,
            deletions=3,
            changed_files=1,
            head_sha="abc123",
        )
        files = [review.ChangedFile("src/router.py", "modified", 42, 3, "@@\n+def route():\n+    return 'ok'\n")]

        body = review.build_review_body(pr, files)

        self.assertIn("Source files changed without test changes", body)
        self.assertIn("`src/router.py` (+42/-3, modified)", body)
        self.assertTrue(body.endswith(review.FRIREN_FOOTER))

    def test_test_files_satisfy_source_test_balance(self) -> None:
        pr = review.PullRequest(
            number=13,
            title="fix: runtime record",
            author="contributor",
            draft=False,
            additions=60,
            deletions=7,
            changed_files=2,
            head_sha="def456",
        )
        files = [
            review.ChangedFile("src/runtime_artifacts.py", "modified", 30, 4, "@@\n+value = 1\n"),
            review.ChangedFile("tests/test_runtime_artifacts.py", "modified", 30, 3, "@@\n+def test_value():\n+    pass\n"),
        ]

        body = review.build_review_body(pr, files)

        self.assertNotIn("without test changes", body)
        self.assertIn("Source: 1 · Tests: 1", body)

    def test_secret_like_assignment_is_flagged(self) -> None:
        pr = review.PullRequest(
            number=14,
            title="chore: config",
            author="contributor",
            draft=False,
            additions=1,
            deletions=0,
            changed_files=1,
            head_sha="abc123",
        )
        files = [review.ChangedFile("examples/config.yaml", "modified", 1, 0, "@@\n+api_key: example\n")]

        body = review.build_review_body(pr, files)

        self.assertIn("Secret-like assignment", body)
        self.assertIn("`examples/config.yaml`", body)


if __name__ == "__main__":
    unittest.main()
