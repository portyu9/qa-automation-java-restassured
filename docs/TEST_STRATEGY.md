# Test strategy

## Purpose

The suite separates fast API/framework contracts from environment-heavy persistence integration while preserving expressive REST Assured assertions. Required API validation runs against repository-owned WireMock fixtures so configuration, schema, diagnostics, protocol composition, and HTTP behavior remain attributable without public-service availability.

## Test layers

| Layer | Maven lifecycle | Target/dependency | Primary concern |
| --- | --- | --- | --- |
| Framework contract | Surefire `test` | No network | Configuration invariants and shared specs |
| API behavior | Surefire `test` | Dynamic-port WireMock | Status, protocol, schema, semantics |
| Native protocol capability | Surefire `test` | Dynamic-port WireMock | Query/path params, extraction, filters, cookies |
| HTTP policy/error behavior | Surefire `test` | Dynamic-port WireMock | Headers, correlation, diagnostics/telemetry |
| Database integration | Failsafe `verify` | Testcontainers 1.21.4 + PostgreSQL 16.15 | Persistence/integration behavior |
| External API integration | Explicit/manual | Configured `TEST_BASE_URL` | Environment/provider behavior |

Fast CI runs on Java 17, 21, and 25. Full `mvn verify` runs on Java 17 in primary CI and Java 25 in extended CI. Java 17 remains the minimum baseline, Java 21 preserves previous-LTS compatibility, and Java 25 qualifies the current LTS without multiplying the expensive container lifecycle across every runtime lane.

## Deterministic API target policy

Required CI must not contact a public demonstration API. `PostsApiFixture` starts WireMock on an ephemeral loopback port and injects a validated `TestConfig` into the provider-neutral `PostsApiClient`.

This preserves a real HTTP boundary: REST Assured still serializes requests, applies filters and timeouts, receives HTTP responses, and exposes native `Response` objects. Only service availability/data are repository-controlled.

External-provider validation is intentionally separate. `TestConfig.fromEnvironment()` requires `TEST_BASE_URL`; no default host is inferred. Missing target configuration fails before transport.

## Configuration-negative testing

`TestConfig` constructor invariants and environment parsing are tested independently. Tests reject:

- missing environment-driven API target;
- URL credentials;
- query-bearing base URIs;
- fragment-bearing base URIs;
- explicit port `0` or values above `65535`;
- non-positive timeout budgets;
- blank, unsafe, or overlong run IDs.

The environment loader accepts an injected read-only lookup so negative tests do not mutate process-global environment state. Universal constructor validation prevents manually built configurations from bypassing policy.

## Native REST Assured capability coverage

Capability tests intentionally use native REST Assured features directly with shared framework policy rather than hiding them behind another request DSL. Required deterministic coverage proves composition of shared request/response specifications, query and path parameters, status/header/body assertions, response extraction, custom filters, and scoped `CookieFilter` state across related requests.

Cookie filters are owned by the test flow that needs session persistence. They are not static/global fixtures because shared cookie state would make tests order-dependent.

## API assertion depth

API tests should combine the relevant layers of evidence: HTTP status, protocol/content type, JSON Schema, semantic values, and domain-specific negative behavior. A schema pass is not sufficient when the wrong resource can still satisfy the same shape. Deterministic fixtures use exact synthetic values so semantic assertions are stable and meaningful.

## Correlation, diagnostics, and telemetry

Every shared request carries a validated run ID; the diagnostics filter generates a per-request ID. On HTTP/transport failure the default diagnostic stream contains structural data only: method, status/error class, duration, request correlation.

Automatic logging deliberately excludes payloads, auth headers, cookies, and raw URLs. `ContractTelemetryFilter` is separate from failure diagnostics and retains only method, sanitized path, status, and duration. Its observation window is bounded, discards oldest entries when full, and returns immutable snapshots under synchronization.

## Timeout and retry policy

Connect/read timeouts are explicit configuration. GitHub Actions jobs are also bounded so infrastructure hangs cannot consume runner capacity indefinitely. The framework does not add blanket retries around REST Assured requests or assertions. Mutating operations require an explicit idempotency contract before retry can be considered safe.

## Database integration policy

Integration tests belong under the Failsafe naming/lifecycle convention and create isolated disposable state through Testcontainers rather than depending on shared developer services.

The PostgreSQL image is explicitly pinned to `postgres:16.15-alpine` so a mutable `16-alpine` tag cannot change the database minor without a repository change. Testcontainers 1.21.4 is deliberately retained for this boundary pending a safe 2.x migration. The attempted 2.0.5 migration compiled on Java 17/21/25 but failed during Docker-client initialization because the assembled runtime exposed an incompatible Jackson annotation version; upstream 2.0.5 also has reported security concerns in its shaded Jackson layer. A future 2.x migration therefore requires both clean integration execution and acceptable upstream dependency security rather than a local compatibility override.

A database-container startup failure is an integration-infrastructure or assembled-runtime failure, not an API assertion failure; Surefire/Failsafe report separation preserves that classification.

## Security topology

Security controls prove different things and remain independent:

- **CodeQL** compiles/analyzes the Java test framework with the `security-extended` query suite;
- **Dependency Review** evaluates dependency changes on pull requests when GitHub Dependency graph data is available;
- **Trivy** scans the repository filesystem for fixed HIGH/CRITICAL dependency findings, supported HIGH/CRITICAL misconfigurations, and committed-secret findings.

If GitHub Dependency graph is unavailable, the workflow says that change-aware review did not run and retains Trivy as an independent whole-repository gate. It does not present the fallback as equivalent to dependency-diff analysis. Security review must also account for dependencies shaded inside tooling libraries when repository-manifest scanning cannot see them directly.

## CI topology

The CI matrix proves distinct properties:

- Java 17, 21, and 25 can compile and execute the deterministic fast API/framework surface;
- Java 17 can complete the full primary `verify` lifecycle;
- Java 25 can complete the full extended `verify` lifecycle, including Testcontainers/PostgreSQL;
- neither API gate depends on public DNS, TLS, third-party data, rate limits, or uptime.

JUnit/Surefire/Failsafe reports are retained for attribution. CI observability identifies the API target class as `local-wiremock`. Maven Enforcer fails unsupported Java/Maven environments before tests begin. Repository security remains separately attributable through CodeQL, graph-aware Dependency Review, and Trivy.

## Failure classification

| Failure class | First interpretation |
| --- | --- |
| Enforcer/build | Toolchain/dependency configuration |
| Framework configuration | Shared input/policy regression |
| WireMock startup/stub verification | Repository-owned HTTP fixture |
| Native query/path/extraction/cookie assertion | Protocol-composition/state contract |
| HTTP status/schema/semantic assertion | API contract/behavior mismatch |
| Request diagnostics transport error | REST Assured/HTTP transport context |
| Telemetry capacity/observation assertion | Structural telemetry policy |
| Failsafe/container | Integration environment, image, or assembled dependency runtime |
| CodeQL | Source-level security finding or analysis/build failure |
| Dependency Review | Newly introduced dependency risk or unavailable graph-backed diff analysis |
| Trivy | Repository dependency/configuration/secret exposure |
| External-target-only failure | Environment/provider integration |

A broad `.log().all()` response dump should not be the default answer to ambiguity. Add the smallest evidence required to classify the failure.

## Exit criteria

A Java API/framework change is ready when:

- Maven Enforcer/build pass;
- fast tests pass on Java 17, 21, and 25;
- constructor and environment configuration-negative contracts pass;
- deterministic WireMock HTTP/schema/semantic contracts pass;
- native query/path/extraction/cookie/filter capability contracts pass;
- telemetry remains bounded and payload-safe;
- full `mvn verify` passes on Java 17 and Java 25 when integration behavior is in scope;
- Testcontainers/PostgreSQL lifecycle remains deterministic against the explicit fixture image;
- major integration-library migrations prove assembled-runtime compatibility rather than compile compatibility alone;
- CodeQL and Trivy pass, and Dependency Review passes when graph-backed diff analysis is available;
- required CI has no public API dependency;
- automatic diagnostics remain payload-safe;
- changes to shared request/target/lifecycle policy are documented and covered by framework tests.
