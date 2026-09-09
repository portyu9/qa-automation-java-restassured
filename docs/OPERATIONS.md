# Operations Guide

## Purpose

This guide owns the detailed operating contract for the Java / REST Assured Quality Engineering Framework: Maven lifecycle, runtime configuration, native REST Assured composition, deterministic WireMock behavior, PostgreSQL/Testcontainers integration, evidence semantics, security, dependency maintenance, and failure triage.

The main [`README.md`](../README.md) is intentionally concise. Deep boundary ownership remains in [`ARCHITECTURE.md`](ARCHITECTURE.md); risk-based layer selection and exit criteria remain in [`TEST_STRATEGY.md`](TEST_STRATEGY.md).

## Quick commands

Prerequisites are a supported Java runtime and a Docker-compatible runtime for PostgreSQL integration. The checked-in Maven Wrapper downloads the repository-pinned Maven distribution and validates its SHA-256.

```bash
# deterministic API/framework contracts
./mvnw -B -ntp -Pfast test

# full API + PostgreSQL lifecycle
./mvnw -B -ntp verify

# documentation + workflow supply-chain contracts
python3 .github/scripts/validate_readme.py
python3 .github/scripts/validate_workflow_pins.py
```

On Windows use `mvnw.cmd` instead of `./mvnw`.

Explicit deployed-provider execution is separate from required framework CI:

```bash
TEST_BASE_URL=https://api.test.example.internal ./mvnw -B -ntp test
```

## Runtime configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `TEST_BASE_URL` | External API base URI | required for environment-driven integration |
| `TEST_CONNECT_TIMEOUT_MS` | Connection budget | `5000` |
| `TEST_READ_TIMEOUT_MS` | Socket/read budget | `15000` |
| `TEST_RUN_ID` | Run correlation | generated UUID |

External base URIs must be absolute HTTP(S), contain a hostname, reject explicit port `0`, and contain no credentials, query string, or fragment. Timeout values must be positive. Unsafe configuration fails before transport creation.

## Maven lifecycle and runtime policy

Maven is part of the test architecture rather than merely a command launcher.

- **Surefire** owns deterministic API/framework contracts.
- **Failsafe** owns `*IntegrationTest`, including PostgreSQL/Testcontainers work.
- the **current qualified Java runtime** executes the complete primary `verify` lifecycle;
- the **minimum supported Java runtime** executes fast compatibility in primary CI and a full extended lifecycle;
- an additional qualified runtime executes fast compatibility;
- future unqualified Java releases remain unsupported until CI and Enforcer policy are deliberately expanded.

The project compiles against the configured minimum Java release policy, and Maven Enforcer bounds both Java and Maven to repository-qualified lines. A future Maven major is not considered supported merely because it happens to launch successfully.

The **Maven Wrapper** is part of build-tool provenance: the selected distribution and checksum are repository-controlled.

## Shared request policy

`ApiSpecs.request(config)` composes cross-cutting transport policy once:

- validated base URI;
- `Accept: application/json`;
- run correlation;
- per-request correlation;
- connection/read budgets;
- bounded failure diagnostics.

Endpoint operations remain explicit in `PostsApiClient`, and native REST Assured `Response` objects remain visible to tests. The abstraction boundary is policy ownership, not syntax replacement.

## API assertion depth

A useful API contract can prove independent dimensions:

1. **Protocol** — status, content type, headers.
2. **Structure** — JSON Schema and required shapes.
3. **Semantics** — identifiers and business-critical values.
4. **Boundary behavior** — invalid input and dependency/error responses.
5. **State** — cookies/session behavior when intentionally required.
6. **Side effects** — persistence when mutation semantics matter.

A schema-valid response can still identify the wrong resource. A `200` can still be semantically wrong. A client assertion does not prove persistence. These are complementary oracles.

## Native REST Assured composition

`RestAssuredCapabilitiesTest` keeps first-class library behavior executable:

- `queryParam()` and `pathParam()` for request composition;
- reusable request/response specs for stable shared policy;
- `.extract().path(...)` for native response extraction;
- scoped `CookieFilter` for deliberately stateful HTTP scenarios;
- `ContractTelemetryFilter` for bounded method/path/status/timing observations;
- Hamcrest and native REST Assured status/header/body assertions.

Do not hide `given()`, request verbs, `.then()`, extraction, filters, or matcher behavior behind a generic second HTTP DSL.

`RequestDiagnosticsFilter` and `ContractTelemetryFilter` have different roles. Diagnostics help classify failures; telemetry provides bounded protocol observations. Neither automatically retains bodies, authorization values, query strings, or cookies.

## Deterministic HTTP boundary

`PostsApiFixture` owns a dynamic-port WireMock server. Tests execute the normal REST Assured/`PostsApiClient` path against it.

WireMock models the provider boundary, not the HTTP client. Serialization, headers, status codes, specifications, filters, extraction, cookies, schema checks, and matchers therefore remain real framework behavior while public DNS, TLS, rate limits, third-party state, and availability are excluded from required CI.

## PostgreSQL integration boundary

`PostgresIntegrationTest` belongs to Failsafe because driver, PostgreSQL dialect, generated identity, and query semantics are material.

The test uses Testcontainers to build the repository-owned `qa-restassured-postgres:16.15-hardened` image from `docker/postgres-test.Dockerfile`. The recipe governs immutable upstream image identities, the gosu source/toolchain, patched OpenSSL floor, and final non-root `postgres` user.

The dedicated **PostgreSQL Testcontainers image gate** independently rebuilds and scans that same tracked image. A green persistence test therefore cannot silently excuse a vulnerable test-runtime image.

Test-owned state uses an isolated container, temporary table, generated identity, parameterized operations, and lifecycle cleanup rather than global row ordering or mutable shared database state.

### Testcontainers major-version boundary

The repository intentionally stays on its currently qualified Testcontainers major. A prior future-major experiment compiled but failed during Docker client initialization because the assembled runtime had incompatible Jackson annotation behavior, and future-major module/package coordinates also changed.

A future migration must prove at least:

- new module/package coordinates compile;
- Docker-client initialization works on supported CI hosts;
- PostgreSQL lifecycle/JDBC contracts pass on minimum and current qualified Java runtimes;
- resolved transitive dependencies have no accepted blocker hidden by shading/assembly;
- dependency and security evidence remain green.

Compile success alone is insufficient qualification.

## Evidence as a test contract

Maven process success is necessary but not sufficient. Repository-owned validation parses `TEST-*.xml` to prove the intended suite executed.

Required fast lanes prove:

- Surefire XML exists;
- at least 14 tests actually executed;
- failures = 0;
- errors = 0;
- skipped = 0.

Full-lifecycle lanes additionally prove:

- Failsafe XML exists;
- at least 1 PostgreSQL integration test executed;
- failures = 0;
- errors = 0;
- skipped = 0.

These floors detect discovery regressions, renamed test patterns, silently skipped integration infrastructure, or artifact upload that succeeds while the intended suite disappears. Evidence uploads use `if-no-files-found: error`.

## Stable CI conclusions

The workflow internals may evolve while stable aggregate status names remain durable:

- `ci / ci-gate` — minimum/additional Java compatibility plus current-runtime full verification;
- `extended / extended-gate` — minimum-supported-runtime full lifecycle;
- `security / security-gate` — source, dependency, hardened PostgreSQL image, repository, and event-applicable dependency-diff controls.

Repository rules/settings remain a separate governance layer.

## Security and supply chain

Security controls answer different questions and remain independently attributable:

- CodeQL `security-extended` analyzes Java source/data flow after controlled compilation;
- CycloneDX produces a test-scope Maven SBOM and the repository validates required REST Assured/JUnit/Testcontainers/PostgreSQL/Jackson components;
- Trivy scans the validated SBOM for fixable HIGH/CRITICAL vulnerabilities;
- the **PostgreSQL Testcontainers image gate** scans the exact repository-built `qa-restassured-postgres:16.15-hardened` image;
- repository Trivy policy inspects supported configuration/secret material separately from Maven dependency resolution;
- Dependency Review analyzes newly introduced dependency risk when GitHub Dependency graph is available;
- Maven Wrapper checksum verification protects build-tool provenance;
- workflow-pin validation requires external GitHub Actions to use full immutable commit SHAs.

Repository-filesystem scanning alone is not treated as proof of the resolved Maven test dependency graph. Missing SBOM or scanner evidence fails closed.

The REST Assured schema-validator transitive graph is aligned through Jackson BOM so governed Jackson components resolve as one compatible patched family. SBOM validation checks that alignment before vulnerability scanning.

## Confidence boundaries

| Signal | Confidence gained | Deliberate limit |
| --- | --- | --- |
| REST Assured API contracts | HTTP status, headers, payload semantics, schema and client-visible errors execute through governed API boundaries | Does not prove browser behavior, live upstreams, or production ingress/network policy |
| JSON Schema | Provider responses retain committed structural shape | Does not prove business semantics or authorization correctness |
| WireMock-controlled dependency | Timeout/error/provider-response conditions are reproducible and attributable | Proves controlled conditions, not current third-party behavior |
| Testcontainers PostgreSQL | JDBC/transaction/query behavior executes against real PostgreSQL built from the hardened repository image | Does not prove managed-service topology, failover, sizing, networking, or deployed migration safety |
| Surefire/Failsafe separation | Fast and infrastructure-bearing tests retain distinct lifecycle/failure attribution | One green phase does not imply the other boundary is healthy |
| SBOM/resolved graph | Build records the dependency graph selected for governed execution | Inventory evidence is not itself a vulnerability verdict |
| Runtime qualification | Same governed suites execute across explicitly supported Java runtimes | Does not cover unqualified future runtimes or every JVM/environment tuning |
| CodeQL / dependency scans / Trivy / Dependency Review | Independent controls inspect source, dependency, repository/configuration, image, and change-diff risk | Scanner success is scoped evidence, not proof of vulnerability absence |

Use real infrastructure when infrastructure semantics are the requirement, not merely to make a test appear more integrated.

## Dependency maintenance

Dependabot maintains **Maven** and **GitHub Actions** dependencies. Maven execution itself is pinned through the checked-in Wrapper and verified distribution checksum.

- weekly Monday maintenance cadence;
- routine minor/patch updates may be grouped;
- major upgrades remain attributable compatibility changes;
- Actions remain immutable-SHA pinned;
- Wrapper changes require deliberate version/checksum changes and full lifecycle verification;
- dependency PRs must satisfy Enforcer, compilation, semantic Surefire/Failsafe evidence, runtime compatibility, test-scope SBOM scanning, hardened PostgreSQL image provenance/scanning, repository security, and docs gates.

Migrations that rename modules/packages require deliberate code changes. The currently qualified Testcontainers major remains automated for maintenance while future-major migration is excluded until its runtime blockers are resolved.

## Failure triage

| Signal | First interpretation |
| --- | --- |
| Enforcer failure | Unsupported Java/Maven runtime |
| Wrapper checksum failure | Build-tool provenance |
| minimum/additional-runtime fast-only | Runtime compatibility or bytecode/API assumption |
| current-runtime full-only | Current runtime or persistence interaction |
| minimum-runtime extended full-only | Minimum-runtime persistence integration |
| Surefire evidence floor | Fast-suite discovery, skip, or report integrity |
| Failsafe evidence floor | Integration discovery/container/report integrity |
| WireMock-only failure | HTTP contract/request policy |
| JSON Schema | Structural/schema-validator compatibility |
| Semantic assertion | API business/data contract |
| CookieFilter | Stateful HTTP semantics |
| PostgreSQL runtime provenance | Dockerfile/Testcontainers/upstream/gosu/OpenSSL/non-root runtime drift |
| PostgreSQL image security | Fixable HIGH/CRITICAL vulnerability in exact repository-built image |
| PostgreSQL Failsafe | Container/driver/SQL/persistence boundary |
| External-target-only | Environment/provider integration first |
| CodeQL | Source-level security signal |
| SBOM validation | Resolved dependency scope/alignment evidence missing or drifted |
| SBOM Trivy | Fixable HIGH/CRITICAL in resolved test dependency graph |
| Repository Trivy | Supported configuration/secret risk |
| Dependency Review unavailable | GitHub service limitation, not a synthetic diff-aware pass |
| Docs/workflow-pin | Repository governance or executable supply-chain drift |

## Explicit anti-patterns

- public demonstration APIs as required CI dependencies;
- validating only HTTP status while ignoring structure and semantics;
- hiding REST Assured behind a generic HTTP wrapper;
- global mutable `RestAssured.baseURI` shared across unrelated tests;
- logging request/response bodies or credentials from global filters;
- containers where a pure/local contract proves the same requirement more cheaply;
- mutable database image tags in deterministic integration gates;
- treating a passing Maven exit code as proof the intended test count ran;
- accepting skipped integration tests as successful persistence evidence;
- treating repository scanning as proof of a resolved Maven test graph;
- overriding a vulnerable Jackson artifact without governing compatible family alignment;
- unbounded Java or Maven support claims without CI qualification;
- forcing ecosystem migrations merely because an updater found a higher version.

## Related documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — configuration, REST Assured, WireMock, PostgreSQL, Maven lifecycle, evidence, security boundaries.
- [`TEST_STRATEGY.md`](TEST_STRATEGY.md) — layer selection, runtime qualification, lifecycle ownership, and exit criteria.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — change-quality expectations.
- [`../.github/SECURITY.md`](../.github/SECURITY.md) — disclosure and repository security policy.

A strong REST Assured framework makes the failed boundary obvious: configuration, HTTP policy, structure, semantics, stateful protocol behavior, runtime compatibility, persistence integration, evidence integrity, supply chain, or explicit environment integration.
