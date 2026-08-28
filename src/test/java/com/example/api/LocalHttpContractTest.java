package com.example.api;

import com.example.framework.TestConfig;
import com.github.tomakehurst.wiremock.WireMockServer;
import io.restassured.response.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.getRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.matching;
import static com.github.tomakehurst.wiremock.client.WireMock.okJson;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.options;
import static org.junit.jupiter.api.Assertions.assertEquals;

class LocalHttpContractTest {
    private WireMockServer server;

    @BeforeEach
    void startServer() {
        server = new WireMockServer(options().dynamicPort());
        server.start();
    }

    @AfterEach
    void stopServer() {
        if (server != null) server.stop();
    }

    private JsonPlaceholderClient client() {
        return new JsonPlaceholderClient(new TestConfig(
                URI.create(server.baseUrl()),
                1_000,
                1_000,
                "wiremock-run"));
    }

    @Test
    void sharedRequestPolicyIsVisibleAtTheHttpBoundary() {
        server.stubFor(get(urlEqualTo("/posts"))
                .willReturn(okJson("""
                        [{"userId":1,"id":1,"title":"local","body":"deterministic"}]
                        """)));

        Response response = client().getPosts();

        assertEquals(200, response.statusCode());
        assertEquals(1, response.jsonPath().getInt("[0].id"));
        server.verify(getRequestedFor(urlEqualTo("/posts"))
                .withHeader("Accept", equalTo("application/json"))
                .withHeader("X-Test-Run-Id", equalTo("wiremock-run"))
                .withHeader("X-Test-Request-Id", matching("[0-9a-fA-F-]{36}")));
    }

    @Test
    void dependencyErrorStatusRemainsObservableToTheTest() {
        server.stubFor(get(urlEqualTo("/posts"))
                .willReturn(aResponse()
                        .withStatus(503)
                        .withHeader("Content-Type", "application/json")
                        .withBody("{\"error\":\"dependency_unavailable\"}")));

        Response response = client().getPosts();

        assertEquals(503, response.statusCode());
        assertEquals("dependency_unavailable", response.jsonPath().getString("error"));
    }
}
