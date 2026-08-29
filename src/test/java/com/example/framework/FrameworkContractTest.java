package com.example.framework;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class FrameworkContractTest {
    @Test
    void environmentConfigurationRequiresAnExplicitTarget() {
        var variables = Map.of(
                "TEST_BASE_URL", "https://api.example.test/v1/",
                "TEST_CONNECT_TIMEOUT_MS", "1200",
                "TEST_READ_TIMEOUT_MS", "3400",
                "TEST_RUN_ID", " framework:contract-42 ");

        var config = TestConfig.fromEnvironment(variables::get);

        assertEquals(URI.create("https://api.example.test/v1"), config.baseUri());
        assertEquals(1_200, config.connectTimeoutMs());
        assertEquals(3_400, config.readTimeoutMs());
        assertEquals("framework:contract-42", config.runId());
    }

    @Test
    void missingEnvironmentTargetFailsBeforeTransport() {
        var error = assertThrows(
                IllegalStateException.class,
                () -> TestConfig.fromEnvironment(name -> null));

        assertTrue(error.getMessage().contains("TEST_BASE_URL"));
    }

    @Test
    void explicitConfigurationCanTargetAnAuthorizedStub() {
        var config = new TestConfig(
                URI.create("http://localhost:8089"),
                1_000,
                2_000,
                "framework-contract");

        var spec = ApiSpecs.request(config);
        assertNotNull(spec);
    }

    @Test
    void configurationRejectsUnsafeUrlsBudgetsAndCorrelationIdentity() {
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://user:password@example.test/api"),
                1_000,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test/api?access_token=secret"),
                1_000,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test/api#fragment"),
                1_000,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test:0"),
                1_000,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test:70000"),
                1_000,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test"),
                0,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test"),
                1_000,
                2_000,
                "unsafe run id"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test"),
                1_000,
                2_000,
                "line-break\nheader"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test"),
                1_000,
                2_000,
                "x".repeat(129)));
    }

    @Test
    void environmentConfigurationRejectsUnsafeTargetsAndInvalidBudgets() {
        var unsafeUrl = Map.of("TEST_BASE_URL", "https://user:password@example.test/api");
        assertThrows(IllegalStateException.class, () -> TestConfig.fromEnvironment(unsafeUrl::get));

        var invalidTimeout = Map.of(
                "TEST_BASE_URL", "https://api.example.test",
                "TEST_READ_TIMEOUT_MS", "0");
        assertThrows(IllegalStateException.class, () -> TestConfig.fromEnvironment(invalidTimeout::get));
    }

    @Test
    void telemetryCapacityMustBePositive() {
        assertThrows(IllegalArgumentException.class, () -> new ContractTelemetryFilter(0));
        assertNotNull(new ContractTelemetryFilter(1));
    }
}
