# Dependabot qualification recovery

## Purpose

Dependency qualification can fail for two fundamentally different reasons: a dependency proposal can be incompatible with the repository, or an otherwise valid qualification run can lose access to a required service for a short period. This repository treats those cases differently without weakening the qualification gates.

`.github/scripts/dependency_recovery.py` may request a single rerun of failed jobs only when the existing Dependabot proposal, existing qualification run, failed job, failed step, and timestamp-bounded log evidence all satisfy the recovery policy. It never edits a Dependabot branch and never merges a pull request. `.github/scripts/dependency_governance.py` remains the only Dependabot merge authority.

## Recovery boundary

Recovery is enabled with `maxRunAttempts: 2`, so an original qualification run can receive at most one automatic rerun attempt. The controller requires the canonical `dependabot[bot]` identity, one verified GitHub-materialized Dependabot commit, a parent equal to the exact current `main` SHA, valid signed Dependabot metadata, an allowed governed ecosystem, and an exact-head pull-request qualification run.

A failed workflow is eligible only when its stable aggregate gate is the single failed gate, every non-gate sibling has a terminal `success`, `skipped`, or `failure` conclusion, and every failed leaf job contains exactly one failed step. Each failed step must match an exact name in `.github/dependency-recovery.json` and contain a recognized transient network or service signature inside that step's own timestamp window. Missing logs, malformed timestamps, mixed failures, ambiguous job conclusions, duplicate or missing gates, stale proposal provenance, and exhausted attempts all fail closed.

The Java allowlist is intentionally narrow. It covers the named Java setup step used by Security and artifact uploads for CI, Extended, and Security evidence. Maven test execution, Maven lifecycle verification, wrapper validation, runtime-policy validation, evidence validators, CycloneDX generation, Docker image builds, Trivy scans, dependency review, CodeQL compilation/analysis, and aggregate gates are not recovery steps.

## Deterministic failures win

The controller checks deterministic or policy-blocking evidence before accepting any transient signature from the same failed step. Maven dependency-resolution failures, missing artifacts, non-resolvable parent POMs, dependency convergence failures, checksum failures, client/policy HTTP statuses such as 400/401/403/404/409/422/429, permission failures, and disk exhaustion block recovery even if the same step also contains a transient-looking string.

Recognized transient evidence is deliberately narrow: DNS retry errors such as `EAI_AGAIN`, connection resets and timeouts, unreachable network/host errors, socket timeouts or hangups, contextual HTTP 502/503/504 responses, exact gateway/service-outage responses, and bounded TLS timeout/unexpected-EOF failures. Generic text such as `Service Unavailable` without an attributable status context is not enough.

## Maven proposals remain manual merge

`pom.xml` co-locates dependency versions, shared family properties, BOM management, Maven plugin versions, runtime enforcement, and test-lifecycle policy. Maven Dependabot proposals therefore remain human-reviewed under `.github/dependency-governance.json` even when a failed qualification job is eligible for transient recovery. A rerun changes only execution state; it does not change the proposal's merge policy.

GitHub Actions dependency proposals retain their existing governance policy. Major or otherwise non-routine action updates remain outside autonomous governance.

## Stale proposals and native rebasing

Every configured Dependabot ecosystem uses `rebase-strategy: auto`. If a proposal is no longer based directly on current `main`, the recovery controller waits for Dependabot's native rebase behavior. It does not call GitHub's update-branch API, push commits to Dependabot branches, or issue synthetic `@dependabot` commands.

## Security and control-plane model

Recovery configuration, recovery code, governance configuration/code, the governance workflow, and `.github/dependabot.yml` are manual-review paths. Pull-request self-tests run with read-only contents permission. The trusted default-branch governance job owns the `actions: write` permission needed to request a failed-job rerun.

A successful rerun is never treated as merge evidence by itself. The ordinary required workflows must finish successfully on the exact Dependabot head, after which dependency governance independently revalidates provenance, signed metadata, ecosystem semantics, and all required aggregate gates before any autonomous merge can occur.

## Operational interpretation

A recovery action means only that a failed infrastructure step had sufficiently narrow transient evidence to justify one more execution attempt. It is not evidence that the dependency update is safe, compatible, or mergeable. If the controller takes no action, inspect the normal qualification failure; deterministic and ambiguous failures are intentionally left for ordinary diagnosis or human review.
