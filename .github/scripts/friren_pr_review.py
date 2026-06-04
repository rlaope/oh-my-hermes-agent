#!/usr/bin/env python3
"""Post a lightweight Friren review comment on pull requests.

The workflow runs from pull_request_target, so this script must only inspect
GitHub API data. It does not check out or execute untrusted PR code.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

FRIREN_FOOTER = "(reviewed by Friren bot)"
API_ROOT = "https://api.github.com"
SECRET_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|private[_-]?key|access[_-]?key)\s*[:=]"
)
SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".sh",
}
TEST_MARKERS = ("test", "tests", "spec", "specs", "__tests__")
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    author: str
    draft: bool
    additions: int
    deletions: int
    changed_files: int
    head_sha: str


@dataclass(frozen=True)
class ChangedFile:
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str = ""

    @property
    def path(self) -> PurePosixPath:
        return PurePosixPath(self.filename)

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @property
    def is_test(self) -> bool:
        parts = tuple(part.lower() for part in self.path.parts)
        stem = self.path.stem.lower()
        return any(marker in parts or stem.startswith(marker + "_") or stem.endswith("_" + marker) for marker in TEST_MARKERS)

    @property
    def is_doc(self) -> bool:
        return self.suffix in DOC_SUFFIXES or any(part.lower() == "docs" for part in self.path.parts)

    @property
    def is_source(self) -> bool:
        return self.suffix in SOURCE_SUFFIXES and not self.is_test

    @property
    def touches_ci_or_workflow(self) -> bool:
        parts = tuple(part.lower() for part in self.path.parts)
        return ".github" in parts or "workflow" in self.filename.lower() or self.suffix in {".yml", ".yaml"}


def _request(method: str, url: str, token: str, data: dict[str, Any] | None = None) -> Any:
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "oh-my-hermes-friren-review",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {url} failed: HTTP {exc.code}: {detail}") from exc


def _paginate(url: str, token: str) -> list[dict[str, Any]]:
    # Keep pagination intentionally small; PR file/comment limits are enough for
    # an automated first-pass review and avoid accidentally expensive runs.
    items: list[dict[str, Any]] = []
    separator = "&" if "?" in url else "?"
    for page in range(1, 6):
        page_items = _request("GET", f"{url}{separator}per_page=100&page={page}", token)
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < 100:
            break
    return items


def load_event(path: str) -> tuple[str, PullRequest]:
    event = json.loads(open(path, encoding="utf-8").read())
    repo = event["repository"]["full_name"]
    pr = event["pull_request"]
    return repo, PullRequest(
        number=int(pr["number"]),
        title=pr.get("title") or "",
        author=pr.get("user", {}).get("login") or "unknown",
        draft=bool(pr.get("draft")),
        additions=int(pr.get("additions") or 0),
        deletions=int(pr.get("deletions") or 0),
        changed_files=int(pr.get("changed_files") or 0),
        head_sha=pr.get("head", {}).get("sha") or "",
    )


def fetch_changed_files(repo: str, pr_number: int, token: str) -> list[ChangedFile]:
    raw_files = _paginate(f"{API_ROOT}/repos/{repo}/pulls/{pr_number}/files", token)
    return [
        ChangedFile(
            filename=str(item.get("filename") or ""),
            status=str(item.get("status") or "modified"),
            additions=int(item.get("additions") or 0),
            deletions=int(item.get("deletions") or 0),
            patch=str(item.get("patch") or ""),
        )
        for item in raw_files
        if item.get("filename")
    ]


def _bullet_files(files: list[ChangedFile], limit: int = 8) -> list[str]:
    bullets = [f"- `{f.filename}` (+{f.additions}/-{f.deletions}, {f.status})" for f in files[:limit]]
    if len(files) > limit:
        bullets.append(f"- …and {len(files) - limit} more file(s)")
    return bullets


def build_review_body(pr: PullRequest, files: list[ChangedFile]) -> str:
    source_files = [item for item in files if item.is_source]
    test_files = [item for item in files if item.is_test]
    doc_files = [item for item in files if item.is_doc]
    ci_files = [item for item in files if item.touches_ci_or_workflow]
    secret_hits = [item for item in files if SECRET_PATTERNS.search(item.patch)]

    findings: list[str] = []
    if pr.draft:
        findings.append("- This is a draft PR. Treat this review as direction-checking rather than a merge gate.")
    if secret_hits:
        findings.append(
            "- ⚠️ Secret-like assignment detected in the diff. If it is a real secret, move it to GitHub Secrets or environment configuration and check whether it was exposed in git history: "
            + ", ".join(f"`{item.filename}`" for item in secret_hits[:5])
        )
    if source_files and not test_files:
        findings.append("- ⚠️ Source files changed without test changes. If this is not a pure refactor or documentation-only behavior change, add at least one focused regression test.")
    if source_files and not doc_files and any(item.additions + item.deletions >= 80 for item in source_files):
        findings.append("- This looks like a sizeable behavior change. If user-facing CLI or workflow behavior changed, update the README or docs as well.")
    if ci_files:
        findings.append("- CI/workflow files changed. If `pull_request_target` or secrets are involved, confirm the workflow does not execute untrusted PR-head code.")
    if pr.changed_files >= 20 or pr.additions + pr.deletions >= 900:
        findings.append("- The change set is large. Consider splitting feature, docs, and cleanup work to keep review manageable.")
    if not findings:
        findings.append("- No obvious automated blocking issue detected. Please confirm tests and CI results before merging.")

    body = [
        "## Friren PR Review",
        "",
        f"PR `#{pr.number}` — **{pr.title}** by `@{pr.author}`",
        "",
        "### Change summary",
        f"- Files: {len(files)} changed / +{pr.additions} / -{pr.deletions}",
        f"- Source: {len(source_files)} · Tests: {len(test_files)} · Docs: {len(doc_files)} · CI/workflows: {len(ci_files)}",
        "",
        "### Files sampled",
        *_bullet_files(files),
        "",
        "### Review notes",
        *findings,
        "",
        "### Suggested human check",
        "- Confirm all CI checks pass",
        "- Confirm changed CLI behavior, docs, and tests describe the same behavior",
        "- Confirm no secret, token, or credential-like value remains in the diff",
        "",
        FRIREN_FOOTER,
    ]
    return "\n".join(body)


def upsert_review_comment(repo: str, pr_number: int, body: str, token: str) -> dict[str, Any]:
    comments = _paginate(f"{API_ROOT}/repos/{repo}/issues/{pr_number}/comments", token)
    for comment in comments:
        existing_body = str(comment.get("body") or "")
        if FRIREN_FOOTER in existing_body:
            return _request("PATCH", comment["url"], token, {"body": body})
    return _request("POST", f"{API_ROOT}/repos/{repo}/issues/{pr_number}/comments", token, {"body": body})


def main() -> int:
    token = os.environ.get("RLAOPE_REVIEW_TOKEN") or os.environ.get("GITHUB_TOKEN")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not token:
        print("RLAOPE_REVIEW_TOKEN/GITHUB_TOKEN is missing; skipping Friren review.")
        return 0
    if not event_path:
        print("GITHUB_EVENT_PATH is missing; skipping Friren review.")
        return 0

    repo, pr = load_event(event_path)
    files = fetch_changed_files(repo, pr.number, token)
    body = build_review_body(pr, files)
    result = upsert_review_comment(repo, pr.number, body, token)
    print(f"Friren review comment ready: {result.get('html_url', 'updated')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
