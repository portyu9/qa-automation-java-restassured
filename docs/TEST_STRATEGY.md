# API and integration test strategy

## Layer selection

Use fast REST Assured tests for protocol/domain behavior that can run against a stable service or stub. Use WireMock to inject deterministic dependency failures. Use Testcontainers for persistence/infrastructure integration. Put full cross-service workflows in a separate higher-level gate.

## API assertions

Cover status, headers/content type, schema, critical values, and side effects. For negative behavior include validation, authentication/authorization, missing resources, conflict/idempotency, malformed input, timeout, and dependency failures where the API contract defines them.

## Schema testing

The JSON Schema validator detects structural drift. Schemas belong in `src/test/resources` and are reviewed like code. Schema success does not imply semantic correctness, so tests still assert key values and workflow outcomes.

## Test data

Create unique test records and clean them up. Avoid shared mutable records and order-dependent IDs. For database cases, Testcontainers gives disposable infrastructure but the test still owns transaction/data cleanup within that container.

## Parallelism

Parallel execution is disabled by default until all shared resources are proven isolated. Enable it deliberately at method/class level only after clients, data, ports, mocks, and containers are concurrency-safe.

## Flake management

Do not add broad automatic retries around assertions. Fix nondeterministic data, eventual consistency, environment saturation, and unbounded calls. If bounded polling is necessary, poll an observable business condition with a defined deadline.

## CI gates

`mvn -Pfast test` is the low-cost feedback gate. `mvn verify` adds `*IntegrationTest` execution. CI retains Surefire/Failsafe reports and tests supported Java runtimes while running infrastructure-heavy verification once to control cost.
