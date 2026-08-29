package com.example.framework;

import java.net.URI;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Pattern;

public record TestConfig(
        URI baseUri,
        int connectTimeoutMs,
        int readTimeoutMs,
        String runId) {

    private static final Pattern SAFE_RUN_ID = Pattern.compile("^[A-Za-z0-9._:-]{1,128}$");

    public TestConfig {
        baseUri = validateHttpBaseUri(baseUri);
        if (connectTimeoutMs <= 0) {
            throw new IllegalArgumentException("connectTimeoutMs must be positive");
        }
        if (readTimeoutMs <= 0) {
            throw new IllegalArgumentException("readTimeoutMs must be positive");
        }
        runId = validateRunId(runId);
    }

    /**
     * Load an explicitly configured deployed/integration target.
     * Deterministic framework tests inject a TestConfig instead of depending on
     * process environment or a public fallback.
     */
    public static TestConfig fromEnvironment() {
        return fromEnvironment(System::getenv);
    }

    static TestConfig fromEnvironment(Function<String, String> readVariable) {
        Objects.requireNonNull(readVariable, "readVariable must not be null");
        return new TestConfig(
                requiredHttpUri(readVariable, "TEST_BASE_URL"),
                positiveInt(readVariable, "TEST_CONNECT_TIMEOUT_MS", 5_000),
                positiveInt(readVariable, "TEST_READ_TIMEOUT_MS", 15_000),
                valueOrDefault(readVariable, "TEST_RUN_ID", UUID.randomUUID().toString()));
    }

    private static URI requiredHttpUri(Function<String, String> readVariable, String name) {
        var raw = readVariable.apply(name);
        if (raw == null || raw.isBlank()) {
            throw new IllegalStateException(name + " is required for environment-driven API integration");
        }
        try {
            return validateHttpBaseUri(URI.create(raw.trim().replaceAll("/+$", "")));
        } catch (IllegalArgumentException error) {
            throw new IllegalStateException(name + " must be a safe absolute http(s) URI", error);
        }
    }

    private static URI validateHttpBaseUri(URI uri) {
        Objects.requireNonNull(uri, "baseUri must not be null");
        var isHttp = "http".equalsIgnoreCase(uri.getScheme()) ||
                "https".equalsIgnoreCase(uri.getScheme());
        if (!uri.isAbsolute() || !isHttp || uri.getHost() == null) {
            throw new IllegalArgumentException("baseUri must be an absolute http(s) URI with a hostname");
        }
        if (uri.getPort() > 65_535) {
            throw new IllegalArgumentException("baseUri port must be between 1 and 65535");
        }
        if (uri.getUserInfo() != null) {
            throw new IllegalArgumentException("baseUri must not contain URL credentials");
        }
        if (uri.getQuery() != null || uri.getFragment() != null) {
            throw new IllegalArgumentException("baseUri must not contain a query string or fragment");
        }
        return uri;
    }

    private static String validateRunId(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("runId must not be blank");
        }
        var normalized = value.trim();
        if (!SAFE_RUN_ID.matcher(normalized).matches()) {
            throw new IllegalArgumentException(
                    "runId must be 1-128 ASCII letters, digits, dots, underscores, colons, or hyphens");
        }
        return normalized;
    }

    private static int positiveInt(
            Function<String, String> readVariable,
            String name,
            int fallback) {
        var raw = readVariable.apply(name);
        if (raw == null || raw.isBlank()) return fallback;
        try {
            int value = Integer.parseInt(raw);
            if (value <= 0) throw new NumberFormatException("not positive");
            return value;
        } catch (NumberFormatException error) {
            throw new IllegalStateException(name + " must be a positive integer", error);
        }
    }

    private static String valueOrDefault(
            Function<String, String> readVariable,
            String name,
            String fallback) {
        var raw = readVariable.apply(name);
        return raw == null || raw.isBlank() ? fallback : raw.trim();
    }
}
