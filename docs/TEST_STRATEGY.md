# Test strategy

## Purpose

The framework separates cheap deterministic API contracts from infrastructure-bearing persistence verification while preserving native REST Assured/JUnit semantics. The strategy optimizes for attributable failures, explicit runtime support, deterministic provider boundaries, and evidence that proves the intended tests actually ran.

## Test planes

| Plane | Runner / tool | Boundary | Required evidence |
| --- | --- | --- | --- |
| Framework policy | JUnit | Configuration/spec/filter policy | Surefire |
| API behavior | REST Assured + JUnit | Dynamic-port WireMock | Surefire |
| Structural contract | JSON Schema | Repository-owned fixture response | Surefire |
| Stateful HTTP | REST Assured `CookieFilter` | Dynamic-port WireMock | Surefire |
| Persistence | JDBC + Testcontainers | PostgreSQL 16.15 | Failsafe |
| Current-LTS lifecycle | Java 25 | Full Maven `verify` | Surefire + Failsafe |
| Minimum-runtime lifecycle | Java 17 | Full Maven `verify` in extended CI | Surefire + Failsafe |
| Intermediate compatibility | Java 21 | Fast deterministic tests | Surefire |
| Security | CodeQL / Trivy / Dependency Review | Source/repository/dependency delta | Security workflow |
| Governance | README/workflow validators | Repository contract | Docs/CI status |

## Fast deterministic gate

Fast tests use repository-owned dynamic-port WireMock and must not require public DNS, public TLS, vendor accounts, rate limits, or mutable third-party data.

The fast layer proves at least:

- runtime/configuration safety;
- shared request specifications;
- protocol status/content-type behavior;
- JSON Schema compatibility;
- business-critical semantic values;
- negative/error behavior;
- request/run correlation;
- path/query composition;
- native response extraction;
- scoped cookie persistence;
- bounded telemetry behavior.

WireMock replaces the provider boundary, not REST Assured. Tests still execute real HTTP through the normal request/client/filter stack.

## Assertion strategy

Prefer layered assertions rather than one broad matcher:

1. **Protocol** — status, content type, required headers.
2. **Structure** — schema/shape.
3. **Semantics** — identifiers and domain-significant values.
4. **Boundary behavior** — invalid inputs and dependency failures.
5. **State** — cookies/session semantics when explicitly required.
6. **Side effects** — persistence or other external-system outcomes when mutation matters.

A successful status code is not a semantic oracle. Schema validity is not a business-value oracle. Keep the failure domain visible.

## Configuration-negative testing

Environment-driven execution must fail before transport when configuration is unsafe or incomplete. Required negative contracts include:

- missing external base URL;
- credentials embedded in URLs;
- query/fragment-bearing targets;
- invalid/zero/out-of-range ports;
- zero/negative timeout budgets;
- unsafe or overlong run identity.

Do not convert configuration mistakes into transport retries.

## Stateful HTTP policy

Use `CookieFilter` only for scenarios that need state continuity. The filter belongs to the smallest scenario or fixture that owns that state.

Do not introduce a global cookie/session filter because it makes order dependence and leaked state invisible.

## Diagnostics and telemetry policy

Global filters must be more privacy-conservative than individual assertions.

Automatic shared evidence may retain bounded:

- method;
- sanitized URL path;
- status;
- elapsed duration;
- run/request identity;
- error class/category.

It must not automatically retain:

- authorization values;
- cookies;
- request/response bodies;
- query strings;
- credential-bearing full URLs.

## Persistence strategy

`PostgresIntegrationTest` belongs to Failsafe. A real PostgreSQL container is justified because driver, SQL dialect, generated keys, and actual persistence/query behavior are material.

The test creates connection-scoped temporary state, inserts an owned row, captures its generated identity, then queries that exact identity. This avoids row-order dependence, pre-existing IDs, and cleanup races.

The image is pinned to `postgres:16.15-alpine`.

Testcontainers remains on 1.21.4 until a 2.x migration proves the runtime, not just compilation. A future migration must verify Docker-client initialization, new module/package coordinates, Java 17 and Java 25 persistence execution, and security/dependency impact.

## Maven lifecycle policy

Surefire owns fast tests. Failsafe owns `*IntegrationTest`.

Use:

```bash
./mvnw -B -ntp -Pfast test
```

for deterministic API/framework feedback and:

```bash
./mvnw -B -ntp verify
```

for the complete lifecycle.

Do not use shell filename filtering to recreate lifecycle semantics outside Maven.

## Java runtime policy

The compiled release remains Java 17. Runtime support is explicitly qualified as:

- **Java 17** — minimum supported runtime;
- **Java 21** — intermediate/previous LTS compatibility;
- **Java 25** — current-LTS primary runtime.

Java 25 runs full `verify` in primary CI. Java 17 and Java 21 run fast compatibility in primary CI, and Java 17 also runs full `verify` in extended CI.

Maven Enforcer accepts Java `[17,26)` only. Do not widen that range until a new runtime has corresponding workflow evidence and documentation.

## Maven toolchain policy

The Wrapper is authoritative:

- Wrapper 3.3.4;
- Maven 3.9.16;
- pinned Maven distribution SHA-256.

Maven Enforcer accepts `[3.9,4)`. Maven 4 is not automatically supported because it is newer; it requires a compatibility change with lifecycle evidence.

## Semantic evidence policy

CI does not equate “Maven exited zero” with “the intended tests ran.”

`.github/scripts/validate_maven_evidence.py` parses Maven XML reports after execution.

Fast lanes must prove:

- Surefire reports exist;
- at least **14 tests executed**;
- zero failures;
- zero errors;
- zero skipped tests.

Full lifecycle lanes must additionally prove:

- Failsafe reports exist;
- at least **1 integration test executed**;
- zero failures;
- zero errors;
- zero skipped integration tests.

If the intended suite deliberately grows or shrinks, change the floor in the same reviewed change and explain why. Do not lower the floor merely to make a discovery regression green.

## Artifact policy

Test evidence is useful only if it exists. Required CI uploads are fail-closed with `if-no-files-found: error`.

Retain:

- Surefire reports for fast lanes;
- Surefire + Failsafe reports for full lifecycle lanes;
- bounded CI observability summaries.

Do not retain credentials or arbitrary provider payloads in generic diagnostics.

## Security policy

Security signals remain separate from test retry policy:

- CodeQL runs Java/Kotlin `security-extended` analysis;
- Trivy gates fixed HIGH/CRITICAL dependency findings, supported HIGH/CRITICAL misconfiguration findings, and committed secret findings;
- Dependency Review gates newly introduced dependency risk when GitHub Dependency graph is available;
- the Maven Wrapper checksum protects the Maven distribution;
- the workflow-pin validator rejects mutable external GitHub Actions.

When Dependency Review is unavailable, record the service limitation. Trivy remains useful, but repository-wide scanning is not equivalent to change-aware dependency-diff analysis.

## Stable status interfaces

The externally meaningful workflow conclusions are:

- `ci / ci-gate`;
- `extended / extended-gate`;
- `security / security-gate`.

Matrix internals can change without constantly changing the stable status vocabulary.

## External integration policy

A deployed target is opt-in through `TEST_BASE_URL`. External integration failures should be classified environment/provider first unless the same contract reproduces against the repository fixture.

Required framework CI should not depend on a public demonstration API merely to appear more end-to-end.

## Failure classification

| Failure class | First interpretation |
| --- | --- |
| Enforcer | Unsupported runtime/toolchain |
| Wrapper checksum | Maven provenance failure |
| Java 17/21 fast | Runtime compatibility / API assumption |
| Java 25 full | Current-LTS / integration interaction |
| Java 17 extended full | Minimum-runtime persistence interaction |
| Surefire evidence | Fast-suite discovery/skips/report integrity |
| Failsafe evidence | Integration discovery/container/report integrity |
| WireMock HTTP | Protocol/request-policy defect |
| JSON Schema | Structural incompatibility |
| Semantic matcher | Wrong business/data result |
| Cookie state | Stateful HTTP ownership |
| PostgreSQL | Driver/container/SQL/persistence boundary |
| CodeQL | Source-level security |
| Trivy | Dependency/configuration/secret security |
| Dependency Review | Newly introduced dependency risk or service availability |
| External target only | Environment/provider integration |

## Exit criteria

A framework change is ready when:

- Enforcer accepts only the deliberately supported Java/Maven envelope;
- the Wrapper checksum and Maven version are correct;
- Java 17 and Java 21 fast compatibility pass;
- Java 25 full lifecycle passes;
- Java 17 extended full lifecycle passes when applicable;
- Surefire evidence proves at least 14 executed tests with no failures/errors/skips;
- Failsafe evidence proves at least one executed integration test with no failures/errors/skips;
- WireMock tests preserve real REST Assured semantics;
- PostgreSQL integration remains deterministic and test-owned;
- Testcontainers 1.21.4 remains the accepted boundary unless a separately proven 2.x migration replaces it;
- shared diagnostics remain bounded and payload-free;
- external GitHub Actions remain immutable-SHA pinned;
- Trivy evidence is present and clean at the configured gate;
- Dependency Review runs when GitHub Dependency graph is available;
- README and workflow documentation describe the implementation truthfully.
