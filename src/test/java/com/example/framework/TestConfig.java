package com.example.framework;

import java.net.URI;
import java.util.UUID;

public record TestConfig(
        URI baseUri,
        int connectTimeoutMs,
        int readTimeoutMs,
        String runId) {

    public static TestConfig fromEnvironment() {
        return new TestConfig(
                absoluteHttpUri("TEST_BASE_URL", "https://jsonplaceholder.typicode.com"),
                positiveInt("TEST_CONNECT_TIMEOUT_MS", 5_000),
                positiveInt("TEST_READ_TIMEOUT_MS", 15_000),
                valueOrDefault("TEST_RUN_ID", UUID.randomUUID().toString()));
    }

    private static URI absoluteHttpUri(String name, String fallback) {
        var raw = valueOrDefault(name, fallback).replaceAll("/+$", "");
        URI uri;
        try {
            uri = URI.create(raw);
        } catch (IllegalArgumentException error) {
            throw new IllegalStateException(name + " must be an absolute http(s) URI", error);
        }
        if (!uri.isAbsolute() || !("http".equals(uri.getScheme()) || "https".equals(uri.getScheme()))) {
            throw new IllegalStateException(name + " must be an absolute http(s) URI");
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
