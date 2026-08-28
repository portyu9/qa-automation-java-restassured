package com.example.framework;

import java.net.URI;
import java.util.Objects;
import java.util.UUID;

public record TestConfig(
        URI baseUri,
        int connectTimeoutMs,
        int readTimeoutMs,
        String runId) {

    public TestConfig {
        baseUri = validateHttpBaseUri(baseUri);
        if (connectTimeoutMs <= 0) {
            throw new IllegalArgumentException("connectTimeoutMs must be positive");
        }
        if (readTimeoutMs <= 0) {
            throw new IllegalArgumentException("readTimeoutMs must be positive");
        }
        if (runId == null || runId.isBlank()) {
            throw new IllegalArgumentException("runId must not be blank");
        }
        runId = runId.trim();
    }

    public static TestConfig fromEnvironment() {
        return new TestConfig(
                absoluteHttpUri("TEST_BASE_URL", "https://jsonplaceholder.typicode.com"),
                positiveInt("TEST_CONNECT_TIMEOUT_MS", 5_000),
                positiveInt("TEST_READ_TIMEOUT_MS", 15_000),
                valueOrDefault("TEST_RUN_ID", UUID.randomUUID().toString()));
    }

    private static URI absoluteHttpUri(String name, String fallback) {
        var raw = valueOrDefault(name, fallback).replaceAll("/+$", "");
        try {
            return URI.create(raw);
        } catch (IllegalArgumentException error) {
            throw new IllegalStateException(name + " must be an absolute http(s) URI", error);
        }
    }

    private static URI validateHttpBaseUri(URI uri) {
        Objects.requireNonNull(uri, "baseUri must not be null");
        var isHttp = "http".equalsIgnoreCase(uri.getScheme()) ||
                "https".equalsIgnoreCase(uri.getScheme());
        if (!uri.isAbsolute() || !isHttp || uri.getHost() == null) {
            throw new IllegalArgumentException("baseUri must be an absolute http(s) URI with a hostname");
        }
        if (uri.getUserInfo() != null) {
            throw new IllegalArgumentException("baseUri must not contain URL credentials");
        }
        if (uri.getQuery() != null || uri.getFragment() != null) {
            throw new IllegalArgumentException("baseUri must not contain a query string or fragment");
        }
        return uri;
    }

    private static int positiveInt(String name, int fallback) {
        var raw = System.getenv(name);
        if (raw == null || raw.isBlank()) return fallback;
        try {
            int value = Integer.parseInt(raw);
            if (value <= 0) throw new NumberFormatException("not positive");
            return value;
        } catch (NumberFormatException error) {
            throw new IllegalStateException(name + " must be a positive integer", error);
        }
    }

    private static String valueOrDefault(String name, String fallback) {
        var raw = System.getenv(name);
        return raw == null || raw.isBlank() ? fallback : raw.trim();
    }
}
