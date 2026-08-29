package com.example.framework;

import io.restassured.filter.Filter;
import io.restassured.filter.FilterContext;
import io.restassured.response.Response;
import io.restassured.specification.FilterableRequestSpecification;
import io.restassured.specification.FilterableResponseSpecification;

import java.net.URI;
import java.util.ArrayDeque;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Records a bounded window of sanitized request/response observations without
 * retaining bodies, credentials, query strings, or cookies.
 */
public final class ContractTelemetryFilter implements Filter {
    public static final int DEFAULT_MAX_OBSERVATIONS = 1_000;

    private final int maxObservations;
    private final ArrayDeque<Observation> observations = new ArrayDeque<>();
    private final Object observationLock = new Object();

    public ContractTelemetryFilter() {
        this(DEFAULT_MAX_OBSERVATIONS);
    }

    public ContractTelemetryFilter(int maxObservations) {
        if (maxObservations < 1) {
            throw new IllegalArgumentException("maxObservations must be positive");
        }
        this.maxObservations = maxObservations;
    }

    @Override
    public Response filter(
            FilterableRequestSpecification requestSpec,
            FilterableResponseSpecification responseSpec,
            FilterContext context) {
        long started = System.nanoTime();
        Response response = context.next(requestSpec, responseSpec);
        long durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

        var observation = new Observation(
                requestSpec.getMethod(),
                sanitizedPath(requestSpec.getURI()),
                response.statusCode(),
                durationMs);

        synchronized (observationLock) {
            if (observations.size() == maxObservations) {
                observations.removeFirst();
            }
            observations.addLast(observation);
        }
        return response;
    }

    public List<Observation> observations() {
        synchronized (observationLock) {
            return List.copyOf(observations);
        }
    }

    private static String sanitizedPath(String uri) {
        try {
            String path = URI.create(uri).getPath();
            return path == null || path.isBlank() ? "/" : path;
        } catch (IllegalArgumentException ignored) {
            return "<invalid-uri>";
        }
    }

    public record Observation(String method, String path, int statusCode, long durationMs) {}
}
