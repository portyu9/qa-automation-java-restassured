# Test strategy

## Purpose

The suite separates fast API/framework contracts from environment-heavy integration tests while preserving expressive REST Assured assertions. Shared infrastructure is tested independently so configuration, schema, or diagnostics regressions do not require a live external failure to identify them.

## Test layers

| Layer | Maven lifecycle | External dependency | Primary concern |
| --- | --- | --- | --- |
| Framework contract | Surefire `test` | No | Configuration invariants and shared specs |
| API behavior | Surefire `test` | HTTP target | Status, protocol, schema, semantics |
| Database integration | Failsafe `verify` | Containerized DB | Persistence/integration behavior |

Fast CI runs on Java 17 and 21. Full `mvn verify` integration coverage runs on the designated baseline runtime so Surefire/Failsafe ownership remains clear.

## Configuration-negative testing

`TestConfig` constructor invariants are tested directly, not only through environment parsing. Tests reject:

- URL credentials;
- query-bearing base URIs;
- fragment-bearing base URIs;
- non-positive timeout budgets;
- blank run IDs.

This matters because helper/client tests may construct `TestConfig` manually. Universal constructor validation prevents those code paths from bypassing production framework policy.

## API assertion depth

API tests should combine the relevant layers of evidence:

1. HTTP status;
2. content type/protocol;
3. JSON Schema;
4. semantic values such as requested ID;
5. domain-specific negative behavior where supported.

A schema pass is not sufficient when the wrong resource can still satisfy the same shape.

## Schema strategy

Keep list and item schemas distinct and version-controlled under `src/test/resources`. Required fields and basic types should match the contract actually asserted by tests.

Schema changes require review like source changes. Do not silently loosen schemas merely to make a provider change pass.

## Correlation and diagnostics

Every shared request carries a run ID; the diagnostics filter generates a per-request ID. On HTTP/transport failure the default diagnostic stream contains structural data only: method, status/error class, duration, request correlation.

Automatic logging deliberately excludes payloads, auth headers, cookies, and URLs. If a failure requires payload evidence, add a narrowly scoped assertion/log at the test/domain boundary using synthetic data rather than enabling global request/response dumps.

## Timeout and retry policy

Connect/read timeouts are explicit configuration. The framework does not add blanket retries around REST Assured requests or assertions. A timeout should fail with enough correlation/timing context to classify the dependency rather than silently execute the operation again.

Mutating operations require an explicit idempotency contract before retry can be considered safe.

## Database integration policy

Integration tests belong under the Failsafe naming/lifecycle convention. They should create isolated disposable state and rely on container lifecycle rather than shared developer services.

A database-container startup failure is an integration-infrastructure failure, not an API assertion failure; Surefire/Failsafe report separation helps preserve that classification.

## CI topology

The CI matrix proves two distinct properties:

- supported Java runtimes can compile and execute the fast test surface;
- the baseline runtime can complete full `mvn verify`, including integrations.

JUnit/Surefire/Failsafe reports are retained for attribution. Maven Enforcer fails unsupported Java/Maven environments before tests begin.

## Failure classification

| Failure class | First interpretation |
| --- | --- |
| Enforcer/build | Toolchain/dependency configuration |
| Framework contract | Shared configuration/spec regression |
| HTTP status/schema/semantic assertion | API contract/behavior mismatch |
| Request diagnostics transport error | Dependency/network failure context |
| Failsafe/container | Integration environment/lifecycle |

A broad `.log().all()` response dump should not be the default answer to ambiguity. Add the smallest evidence required to classify the failure.

## Exit criteria

A Java API/framework change is ready when:

- Maven Enforcer/build pass;
- fast tests pass on the supported Java matrix;
- constructor/configuration-negative contracts pass;
- schema and semantic assertions pass;
- full `mvn verify` passes when integration behavior is in scope;
- automatic diagnostics remain payload-safe;
- changes to shared request/lifecycle policy are documented and covered by framework tests.
