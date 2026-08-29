package com.example.api;

import com.example.testing.PostsApiFixture;
import io.restassured.response.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.getRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.matching;
import static com.github.tomakehurst.wiremock.client.WireMock.okJson;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static org.junit.jupiter.api.Assertions.assertEquals;

class LocalHttpContractTest {
    private PostsApiFixture fixture;

    @BeforeEach
    void startServer() {
        fixture = new PostsApiFixture();
    }

    @AfterEach
    void stopServer() {
        if (fixture != null) fixture.close();
    }

    private PostsApiClient client() {
        return new PostsApiClient(fixture.config("wiremock-run"));
    }

    @Test
    void sharedRequestPolicyIsVisibleAtTheHttpBoundary() {
        fixture.server().stubFor(get(urlEqualTo("/posts"))
                .willReturn(okJson("""
                        [{"userId":1,"id":1,"title":"local","body":"deterministic"}]
                        """)));

        Response response = client().getPosts();

        assertEquals(200, response.statusCode());
        assertEquals(1, response.jsonPath().getInt("[0].id"));
        fixture.server().verify(getRequestedFor(urlEqualTo("/posts"))
                .withHeader("Accept", matching(".*application/json.*"))
                .withHeader("X-Test-Run-Id", equalTo("wiremock-run"))
                .withHeader("X-Test-Request-Id", matching("[0-9a-fA-F-]{36}")));
    }

    @Test
    void dependencyErrorStatusRemainsObservableToTheTest() {
        fixture.server().stubFor(get(urlEqualTo("/posts"))
                .willReturn(aResponse()
                        .withStatus(503)
                        .withHeader("Content-Type", "application/json")
                        .withBody("{\"error\":\"dependency_unavailable\"}")));

        Response response = client().getPosts();

        assertEquals(503, response.statusCode());
        assertEquals("dependency_unavailable", response.jsonPath().getString("error"));
    }
}
