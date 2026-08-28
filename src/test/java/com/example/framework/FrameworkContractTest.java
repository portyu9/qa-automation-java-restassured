package com.example.framework;

import org.junit.jupiter.api.Test;

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
                java.net.URI.create("http://localhost:8089"),
                1_000,
                2_000,
                "framework-contract");

        var spec = ApiSpecs.request(config);
        assertNotNull(spec);
    }
}
