# Architecture

## Boundaries

- **Tests** own behavior assertions and scenario intent.
- **Domain clients** expose API operations without embedding assertions unrelated to transport contracts.
- **Request/response specifications** centralize base URI, safe common headers, timeouts, content type, and failure logging policy.
- **Configuration** converts environment variables into typed immutable state.
- **WireMock** provides deterministic dependency behavior where a real dependency is not the subject of the test.
- **Testcontainers** provides disposable infrastructure for integration tests.

Avoid static global mutation of `RestAssured.baseURI` in parallel-capable suites. Passing a reusable request specification into `given().spec(...)` keeps target configuration explicit and easier to isolate.

## Specifications

Request specifications are appropriate for transport policy shared by a service. Response specifications should contain invariants such as content type, not endpoint-specific status codes or business fields. Endpoint assertions remain visible in tests.

## Timeouts

Connection and read timeouts are mandatory and validated. An API test that can wait indefinitely consumes CI capacity and produces poor failure diagnostics.

## Correlation

Every client request carries `X-Test-Run-Id`. In real systems, capture server-generated correlation/trace IDs from responses and include them in failure diagnostics. Never log authorization tokens, cookies, credentials, or sensitive payload fields.

## Integration split

Surefire executes fast `*Test` classes. Failsafe owns `*IntegrationTest` classes during `mvn verify`. This makes the difference between component behavior and infrastructure-backed verification visible in Maven lifecycle semantics.

## Mocks versus real systems

WireMock should model explicit external boundaries and failure modes. Do not mock the class under test or duplicate internal implementation. Keep at least one appropriate real integration/contract gate so mocks cannot silently diverge from the provider.
