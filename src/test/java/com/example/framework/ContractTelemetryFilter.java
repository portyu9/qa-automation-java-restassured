package com.example.framework;

import io.restassured.filter.Filter;
import io.restassured.filter.FilterContext;
import io.restassured.response.Response;
import io.restassured.specification.FilterableRequestSpecification;
import io.restassured.specification.FilterableResponseSpecification;

import java.net.URI;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;

/**
 * Records sanitized request/response observations without retaining bodies,
 * credentials, query strings, or cookies.
 */
public final class ContractTelemetryFilter implements Filter {
    private final ConcurrentLinkedQueue<Observation> observations = new ConcurrentLinkedQueue<>();

    @Override
    public Response filter(
            FilterableRequestSpecification requestSpec,
            FilterableResponseSpecification responseSpec,
            FilterContext context) {
        long started = System.nanoTime();
        Response response = context.next(requestSpec, responseSpec);
        long durationMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);

        observations.add(new Observation(
                requestSpec.getMethod(),
                sanitizedPath(requestSpec.getURI()),
                response.statusCode(),
                durationMs));
        return response;
    }

    public List<Observation> observations() {
        return List.copyOf(observations);
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
