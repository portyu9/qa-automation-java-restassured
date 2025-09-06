# QA Automation: Java RestAssured Sample

I created this repository to demonstrate a production‑grade API and database test automation framework in Java. This project uses modern libraries such as **RestAssured** for HTTP assertions, **Testcontainers** for spinning up disposable PostgreSQL databases during integration tests, and **WireMock** for mocking external services. The test suite targets a real public API (JSONPlaceholder) and includes examples of contract validation, service‑layer tests and data persistence checks.

## Features

- **API tests with RestAssured and JUnit 5.** I wrote concise and expressive tests against live endpoints.
- **Contract validation using JSON Schema.** Each response is checked against a schema located in `src/test/resources`.
- **Integration tests using Testcontainers** to start a temporary PostgreSQL database. I use JDBC to verify data persistence.
- **Mocking of external dependencies with WireMock.** The framework can be extended to simulate third‑party services.
- **Clean project structure** following a Page Object–style abstraction for service endpoints.
- **Extensible test data management** to keep fixtures and schemas organized.
- **Continuous integration configuration via GitHub Actions.** Tests run automatically on every push or pull request.

## Getting Started

### Prerequisites

- Java 17 or later.
- Maven 3.9+.

### Running the Tests

I can run the entire test suite locally with:

```bash
mvn test
```

Maven will download all dependencies, start a containerised PostgreSQL database for the integration tests, run WireMock for the mocked endpoints, and execute the JUnit tests.

### Project Structure

- `src/test/java/com/example/api` – API tests and abstractions.
- `src/test/java/com/example/db` – Database integration tests.
- `.github/workflows/ci.yml` – GitHub Actions workflow to run tests in CI.

## About the Public API

The API tests target [JSONPlaceholder](https://jsonplaceholder.typicode.com/), a free REST API for prototyping and testing. I selected it because it is stable and freely available.

## Continuous Integration

GitHub Actions will automatically run on every push and pull request. The workflow sets up the correct Java version, caches Maven dependencies and runs `mvn test`. Failing tests will mark the build as failed.
