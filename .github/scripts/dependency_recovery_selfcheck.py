#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dependency_governance import load_config  # noqa: E402
from dependency_recovery import (  # noqa: E402
    _workflow_run_pull,
    classify_leaf_job_failure,
    classify_run_failure,
    extract_step_log_window,
    matching_non_transient_signatures,
    matching_transient_signatures,
    recover_pull,
    recovery_scope_assessment,
    validate_recovery_config,
)

ROOT = SCRIPT_DIR.parents[1]
GOVERNANCE = load_config()
RECOVERY = json.loads((ROOT / ".github" / "dependency-recovery.json").read_text(encoding="utf-8"))
SUCCESS_START = "2026-09-16T12:00:00Z"
SUCCESS_END = "2026-09-16T12:00:02Z"
FAILURE_START = "2026-09-16T12:00:03Z"
FAILURE_END = "2026-09-16T12:00:05Z"


def log_line(timestamp: str, message: str) -> str:
    return f"{timestamp} {message}"


def logs(before: str = "", failed: str = "", after: str = "") -> str:
    return "\n".join(
        (
            log_line("2026-09-16T12:00:01.0000000Z", before),
            log_line("2026-09-16T12:00:04.0000000Z", failed),
            log_line("2026-09-16T12:00:06.0000000Z", after),
        )
    )


def job(
    *,
    job_id: int = 10,
    name: str = "Java 25 current-LTS full verify",
    step: str = "Upload current-LTS evidence",
    conclusion: str | None = "failure",
    started_at: str | None = FAILURE_START,
    completed_at: str | None = FAILURE_END,
) -> dict[str, Any]:
    return {
        "id": job_id,
        "name": name,
        "conclusion": conclusion,
        "steps": [
            {
                "name": "Set up job",
                "conclusion": "success",
                "started_at": SUCCESS_START,
                "completed_at": SUCCESS_END,
            },
            {
                "name": step,
                "conclusion": conclusion,
                "started_at": started_at,
                "completed_at": completed_at,
            },
        ],
    }


def gate(name: str = "ci-gate", conclusion: str = "failure") -> dict[str, Any]:
    return {
        "id": 99,
        "name": name,
        "conclusion": conclusion,
        "steps": [
            {
                "name": "Evaluate required CI jobs",
                "conclusion": conclusion,
                "started_at": FAILURE_START,
                "completed_at": FAILURE_END,
            }
        ],
    }


def canonical_fixture() -> dict[str, Any]:
    base_sha = "a" * 40
    head_sha = "b" * 40
    full_name = "portyu9/fixture"
    pull = {
        "number": 61,
        "state": "open",
        "user": {"login": GOVERNANCE["botLogin"], "id": GOVERNANCE["botUserId"]},
        "base": {"ref": "main", "sha": base_sha, "repo": {"full_name": full_name}},
        "head": {
            "ref": "dependabot/github_actions/routine-actions",
            "repo": {"full_name": full_name},
            "sha": head_sha,
        },
        "draft": False,
        "labels": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "commits": 1,
        "changed_files": 1,
    }
    commit = {
        "sha": head_sha,
        "author": {"login": GOVERNANCE["botLogin"], "id": GOVERNANCE["botUserId"]},
        "committer": {"login": GOVERNANCE["trustedCommitterLogin"]},
        "commit": {
            "author": {"name": GOVERNANCE["botLogin"], "email": GOVERNANCE["botAuthorEmail"]},
            "committer": {
                "name": GOVERNANCE["gitCommitterName"],
                "email": GOVERNANCE["gitCommitterEmail"],
            },
            "verification": {"verified": True, "reason": "valid", "signature": "fixture-signature"},
            "message": (
                "deps(deps): bump actions/checkout\n\n---\nupdated-dependencies:\n"
                "- dependency-name: actions/checkout\n"
                "  dependency-version: '7.0.2'\n"
                "  dependency-type: direct:production\n"
                "  update-type: version-update:semver-patch\n"
                "...\n\n"
                + GOVERNANCE["signedOffBy"]
            ),
        },
        "parents": [{"sha": base_sha}],
    }
    return {"base_sha": base_sha, "head_sha": head_sha, "pull": pull, "commit": commit}


def workflow_run(fixture: dict[str, Any]) -> dict[str, Any]:
    requirement = GOVERNANCE["requiredWorkflows"][0]
    return {
        "id": 501,
        "name": requirement["workflow"],
        "path": f".github/workflows/{requirement['file']}",
        "event": "pull_request",
        "head_sha": fixture["head_sha"],
        "head_branch": fixture["pull"]["head"]["ref"],
        "pull_requests": [{"number": fixture["pull"]["number"]}],
        "status": "completed",
        "conclusion": "failure",
        "run_attempt": 1,
        "updated_at": "2026-09-16T12:00:10Z",
    }


class FakeApi:
    def __init__(self, fixture: dict[str, Any], *, run: dict[str, Any], jobs: list[dict[str, Any]]) -> None:
        self.owner = "portyu9"
        self.repo = "fixture"
        self.fixture = fixture
        self.run = run
        self.jobs = jobs
        self.reruns: list[int] = []

    def get(self, path: str) -> Any:
        if path == f"/pulls/{self.fixture['pull']['number']}":
            return self.fixture["pull"]
        if path == "/git/ref/heads/main":
            return {"object": {"sha": self.fixture["base_sha"]}}
        raise AssertionError(f"unexpected GET {path}")

    def paginate(self, path: str, selector: str | None = None) -> list[Any]:
        number = self.fixture["pull"]["number"]
        if path.startswith(f"/pulls/{number}/files"):
            return [{"filename": ".github/workflows/ci.yml"}]
        if path.startswith(f"/pulls/{number}/commits"):
            return [self.fixture["commit"]]
        if path.startswith("/actions/runs?"):
            return [self.run]
        if path.startswith(f"/actions/runs/{self.run['id']}/jobs"):
            return self.jobs
        if path == "/pulls?state=open":
            return [self.fixture["pull"]]
        raise AssertionError(f"unexpected paginate {path} selector={selector}")

    def post(self, path: str, payload: dict[str, Any]) -> None:
        match = re.fullmatch(r"/actions/runs/(\d+)/rerun-failed-jobs", path)
        if not match:
            raise AssertionError(f"unexpected POST {path}")
        self.reruns.append(int(match.group(1)))


class RecoverySelfCheck(unittest.TestCase):
    def test_config_is_bounded_and_only_exact_infrastructure_steps(self) -> None:
        self.assertEqual(validate_recovery_config(RECOVERY), [])
        self.assertEqual(RECOVERY["maxRunAttempts"], 2)
        expected = {
            "Set up Java 25 LTS",
            "Upload compatibility evidence",
            "Upload current-LTS evidence",
            "Upload extended evidence",
            "Upload Maven dependency security evidence",
            "Upload PostgreSQL image security evidence",
            "Upload repository security evidence",
        }
        self.assertEqual(set(RECOVERY["transientSteps"]), expected)
        for forbidden in (
            "Verify checksum-pinned Maven wrapper",
            "Fast API and framework tests against repository-owned WireMock fixtures",
            "Run full lifecycle including local HTTP and PostgreSQL integration contracts",
            "Compile test framework for CodeQL",
            "Generate CycloneDX SBOM including test dependencies",
            "Scan test-scope SBOM for HIGH/CRITICAL vulnerabilities",
            "Build exact Testcontainers image",
            "Scan exact Testcontainers image for HIGH/CRITICAL vulnerabilities",
            "Scan repository configuration and secrets",
            "Review dependency changes",
            "Analyze",
            "Evaluate required CI jobs",
            "Evaluate extended lifecycle job",
            "Evaluate security jobs",
        ):
            self.assertNotIn(forbidden, RECOVERY["transientSteps"], forbidden)
        self.assertTrue(validate_recovery_config({**RECOVERY, "maxRunAttempts": 4}))

    def test_signature_model_is_narrow_and_blockers_win(self) -> None:
        self.assertEqual(matching_transient_signatures("npm error code EAI_AGAIN"), ["dns-eai-again"])
        self.assertEqual(matching_transient_signatures("HTTP 503"), ["http-5xx"])
        self.assertEqual(matching_transient_signatures("Service Unavailable"), [])
        self.assertIn("maven-resolution", matching_non_transient_signatures("Could not find artifact x:y:jar:9"))
        self.assertIn("maven-checksum", matching_non_transient_signatures("checksum mismatch for wrapper"))
        self.assertIn("http-client-or-policy", matching_non_transient_signatures("HTTP 403"))

    def test_only_failed_step_timestamp_window_can_authorize_retry(self) -> None:
        candidate = job()
        window = extract_step_log_window(
            logs("EAI_AGAIN", "HTTP 403", "503 Service Unavailable"), candidate["steps"][1]
        )
        self.assertIsNotNone(window)
        assert window is not None
        self.assertIn("HTTP 403", window)
        self.assertNotIn("EAI_AGAIN", window)
        result = classify_leaf_job_failure(candidate, logs("EAI_AGAIN", "HTTP 403"), RECOVERY)
        self.assertFalse(result["transient"])
        self.assertIn("deterministic or policy-blocking", result["reason"])

    def test_allowlisted_infrastructure_failure_is_retryable_only_with_transient_evidence(self) -> None:
        positive = classify_leaf_job_failure(job(), logs(failed="ECONNRESET"), RECOVERY)
        self.assertTrue(positive["transient"], positive["reason"])
        absent = classify_leaf_job_failure(job(), logs(failed="artifact upload failed"), RECOVERY)
        self.assertFalse(absent["transient"])

    def test_functional_and_security_steps_never_become_transient(self) -> None:
        for step in (
            "Verify checksum-pinned Maven wrapper",
            "Fast API and framework tests against repository-owned WireMock fixtures",
            "Run full lifecycle including local HTTP and PostgreSQL integration contracts",
            "Validate semantic Surefire and Failsafe evidence",
            "Compile test framework for CodeQL",
            "Generate CycloneDX SBOM including test dependencies",
            "Scan test-scope SBOM for HIGH/CRITICAL vulnerabilities",
            "Build exact Testcontainers image",
            "Scan exact Testcontainers image for HIGH/CRITICAL vulnerabilities",
            "Scan repository configuration and secrets",
            "Review dependency changes",
            "Analyze",
        ):
            result = classify_leaf_job_failure(job(step=step), logs(failed="EAI_AGAIN HTTP 503"), RECOVERY)
            self.assertFalse(result["transient"], step)

    def test_missing_or_malformed_step_timestamps_fail_closed(self) -> None:
        for candidate in (
            job(started_at=None),
            job(completed_at=None),
            job(started_at="not-a-date"),
            job(started_at=FAILURE_END, completed_at=FAILURE_START),
        ):
            result = classify_leaf_job_failure(candidate, logs(failed="EAI_AGAIN"), RECOVERY)
            self.assertFalse(result["transient"])
            self.assertIn("timestamp-bounded log window", result["reason"])

    def test_run_requires_failed_gate_unambiguous_siblings_and_first_attempt(self) -> None:
        run = {"status": "completed", "conclusion": "failure", "run_attempt": 1}
        positive = classify_run_failure(
            run, [job(), gate()], {10: logs(failed="EAI_AGAIN")}, "ci-gate", RECOVERY
        )
        self.assertTrue(positive["rerunnable"], positive["reason"])
        for conclusion in ("cancelled", "timed_out", "neutral", "action_required", "stale", None):
            sibling = {"id": 20, "name": "sibling", "conclusion": conclusion, "steps": []}
            blocked = classify_run_failure(
                run, [job(), sibling, gate()], {10: logs(failed="EAI_AGAIN")}, "ci-gate", RECOVERY
            )
            self.assertFalse(blocked["rerunnable"], str(conclusion))
        capped = classify_run_failure(
            {"status": "completed", "conclusion": "failure", "run_attempt": 2},
            [job(), gate()],
            {10: logs(failed="EAI_AGAIN")},
            "ci-gate",
            RECOVERY,
        )
        self.assertFalse(capped["rerunnable"])
        self.assertIn("recovery cap", capped["reason"])

    def test_manual_maven_recovery_never_changes_manual_merge_policy(self) -> None:
        result = recovery_scope_assessment(
            pull={"changed_files": 1},
            files=[{"filename": "pom.xml"}],
            provenance={"eligible": True, "reasons": []},
            metadata={"eligible": True, "reasons": [], "metadata": []},
            governance_config=GOVERNANCE,
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["ecosystem"], "maven")
        self.assertEqual(result["mergePolicy"], "manual")
        self.assertEqual(GOVERNANCE["ecosystems"]["maven"]["mode"], "manual")

    def test_control_plane_paths_are_recovery_ineligible(self) -> None:
        for path in (
            ".github/dependabot.yml",
            ".github/dependency-governance.json",
            ".github/dependency-recovery.json",
            ".github/scripts/dependency_governance.py",
            ".github/scripts/dependency_governance_selfcheck.py",
            ".github/scripts/dependency_recovery.py",
            ".github/scripts/dependency_recovery_selfcheck.py",
            ".github/workflows/dependency-governance.yml",
        ):
            self.assertIn(path, GOVERNANCE["manualReviewPaths"], path)

    def test_exact_provenance_positive_path_requests_one_rerun(self) -> None:
        fixture = canonical_fixture()
        run = workflow_run(fixture)
        api = FakeApi(fixture, run=run, jobs=[job(), gate()])
        result = recover_pull(
            api,
            fixture["pull"]["number"],
            GOVERNANCE,
            RECOVERY,
            True,
            log_loader=lambda _api, _job_id: logs(failed="EAI_AGAIN"),
        )
        self.assertEqual(api.reruns, [run["id"]])
        self.assertEqual(result["actions"][0]["state"], "rerun-requested")

    def test_stale_base_waits_for_native_dependabot_rebase_without_mutation(self) -> None:
        fixture = canonical_fixture()
        run = workflow_run(fixture)
        api = FakeApi(fixture, run=run, jobs=[job(), gate()])
        fixture["commit"]["parents"] = [{"sha": "c" * 40}]
        result = recover_pull(
            api,
            fixture["pull"]["number"],
            GOVERNANCE,
            RECOVERY,
            True,
            log_loader=lambda _api, _job_id: logs(failed="EAI_AGAIN"),
        )
        self.assertEqual(api.reruns, [])
        self.assertTrue(result["skipped"])
        self.assertIn("native auto-rebase", result["reason"])

    def test_workflow_run_branch_resolution_accepts_only_dependabot_branch(self) -> None:
        fixture = canonical_fixture()
        run = workflow_run(fixture)
        api = FakeApi(fixture, run=run, jobs=[])
        previous = {name: os.environ.get(name) for name in ("TARGET_PR_NUMBER", "WORKFLOW_RUN_HEAD_BRANCH")}
        try:
            os.environ.pop("TARGET_PR_NUMBER", None)
            os.environ["WORKFLOW_RUN_HEAD_BRANCH"] = fixture["pull"]["head"]["ref"]
            self.assertEqual(_workflow_run_pull(api), fixture["pull"]["number"])
            os.environ["WORKFLOW_RUN_HEAD_BRANCH"] = "feature/not-dependabot"
            self.assertIsNone(_workflow_run_pull(api))
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_wiring_requires_auto_rebase_protected_paths_and_recovery_before_merge(self) -> None:
        dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "dependency-governance.yml").read_text(encoding="utf-8")
        self.assertEqual(dependabot.count("rebase-strategy: auto"), 2)
        self.assertIn("RECOVERY_CONFIG: .github/dependency-recovery.json", workflow)
        self.assertIn("python .github/scripts/dependency_recovery.py --validate-config", workflow)
        self.assertIn("python .github/scripts/dependency_recovery_selfcheck.py", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("ALLOW_RECOVERY_RERUN:", workflow)
        self.assertLess(
            workflow.index("Attempt bounded dependency recovery"),
            workflow.index("Reconcile dependency governance"),
        )
        self.assertNotIn("update-branch", (SCRIPT_DIR / "dependency_recovery.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
