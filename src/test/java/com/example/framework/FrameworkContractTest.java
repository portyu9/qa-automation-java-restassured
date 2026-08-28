package com.example.framework;

import org.junit.jupiter.api.Test;

import java.net.URI;

import static org.junit.jupiter.api.Assertions.*;

class FrameworkContractTest {
    @Test
    void defaultConfigurationIsValid() {
        var config = TestConfig.fromEnvironment();

        assertTrue(config.baseUri().isAbsolute());
        assertTrue(config.connectTimeoutMs() > 0);
        assertTrue(config.readTimeoutMs() > 0);
        assertFalse(config.runId().isBlank());
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
    void configurationRejectsUnsafeUrlsAndInvalidBudgets() {
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
                URI.create("https://example.test"),
                0,
                2_000,
                "run"));
        assertThrows(IllegalArgumentException.class, () -> new TestConfig(
                URI.create("https://example.test"),
                1_000,
                2_000,
                "  "));
    }
}
