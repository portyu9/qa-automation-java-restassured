package com.example.framework;

import io.restassured.filter.Filter;
import io.restassured.filter.FilterContext;
import io.restassured.response.Response;
import io.restassured.specification.FilterableRequestSpecification;
import io.restassured.specification.FilterableResponseSpecification;

import java.util.UUID;

/**
 * Adds a unique correlation id to every HTTP request and emits only bounded,
 * non-payload diagnostics for dependency failures. Request/response bodies are
 * intentionally excluded from automatic logging.
 */
public final class RequestDiagnosticsFilter implements Filter {
    @Override
    public Response filter(
            FilterableRequestSpecification requestSpec,
            FilterableResponseSpecification responseSpec,
            FilterContext context) {
        var requestId = UUID.randomUUID().toString();
        requestSpec.header("X-Test-Request-Id", requestId);
        var started = System.nanoTime();

        try {
            var response = context.next(requestSpec, responseSpec);
            var elapsedMs = (System.nanoTime() - started) / 1_000_000;
            if (response.statusCode() >= 400) {
                System.err.printf(
                        "[api-request:%s] method=%s status=%d durationMs=%d%n",
                        requestId,
                        requestSpec.getMethod(),
                        response.statusCode(),
                        elapsedMs);
            }
            return response;
        } catch (RuntimeException error) {
            var elapsedMs = (System.nanoTime() - started) / 1_000_000;
            System.err.printf(
                    "[api-request:%s] method=%s transportError=%s durationMs=%d%n",
                    requestId,
                    requestSpec.getMethod(),
                    error.getClass().getSimpleName(),
                    elapsedMs);
            throw error;
        }
    }
}
