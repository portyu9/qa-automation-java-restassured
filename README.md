# Java / REST Assured API Test Framework

A Java 17+ API automation framework using REST Assured, JUnit 5, JSON Schema validation, WireMock, Testcontainers, and Maven lifecycle separation for fast and infrastructure-backed tests.

## Technology baseline

- Java 17 minimum;
- REST Assured 6.0.1;
- JUnit Jupiter;
- JSON Schema Validator;
- WireMock for controlled external dependencies;
- Testcontainers/PostgreSQL for disposable integration infrastructure;
- Surefire for `*Test` and Failsafe for `*IntegrationTest`.

## Structure

```text
.
├── src/test/java/com/example/
│   ├── api/
│   ├── db/
│   └── framework/
│       ├── TestConfig.java
│       └── ApiSpecs.java
├── src/test/resources/
│   └── post-schema.json
├── docs/
├── pom.xml
└── .github/workflows/ci.yml
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `TEST_BASE_URL` | API target | JSONPlaceholder |
| `TEST_CONNECT_TIMEOUT_MS` | connection timeout | `5000` |
| `TEST_READ_TIMEOUT_MS` | response read timeout | `15000` |
| `TEST_RUN_ID` | request/run correlation | generated UUID |

Configuration is converted into immutable `TestConfig` state before requests are created. `.env.example` is documentation; inject environment values through the shell or CI.

## Commands

Fast tests only:

```bash
mvn -Pfast test
```

Full Maven verification including `*IntegrationTest` through Failsafe:

```bash
mvn verify
```

Single API test:

```bash
mvn -Dtest=PostApiTest test
```

## Request/response specification policy

`ApiSpecs.request()` centralizes base URI, explicit connection/read timeouts, accepted content type, and run correlation. `ApiSpecs.jsonResponse()` contains only cross-endpoint response invariants.

Endpoint-specific status codes and domain values stay in tests. Avoid hiding entire requests behind generic wrappers; domain clients such as `JsonPlaceholderClient` should expose meaningful service operations.

## REST Assured logging

Response logging is enabled only when validation fails. In authenticated systems, add filters that redact `Authorization`, cookies, API keys, passwords, and sensitive payload fields before enabling request logging.

## Mocks and contracts

WireMock is appropriate for injecting timeouts, malformed responses, 4xx/5xx behavior, and deterministic provider cases. A mock should verify the outgoing request contract and should not replace every real integration path.

JSON Schema assertions protect response structure. They complement, rather than replace, behavioral assertions and provider compatibility checks.

## Database integration

Classes ending in `IntegrationTest` execute in Maven Failsafe during `verify`. Testcontainers provides disposable PostgreSQL infrastructure so integration state is isolated from developer/shared databases.

## CI

GitHub Actions runs the fast gate on Java 17 and 21, executes full integration verification on Java 17, caches Maven dependencies, and retains Surefire/Failsafe reports on failure. Maven Enforcer rejects unsupported Java/Maven runtimes before tests start.

## Extension rules

- add target configuration through `TestConfig` with validation;
- put transport invariants in specs, domain behavior in tests;
- give all network calls bounded timeouts;
- prefer unique, disposable test data;
- keep mocks at external boundaries;
- separate integration tests through naming/lifecycle, not comments;
- capture correlation IDs and safe diagnostics for CI triage.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md) for design and governance details.
