package com.example.api;

import com.example.framework.ApiSpecs;
import com.example.framework.ContractTelemetryFilter;
import com.example.framework.TestConfig;
import com.github.tomakehurst.wiremock.WireMockServer;
import io.restassured.filter.cookie.CookieFilter;
import org.junit.jupiter.api.Test;

import java.net.URI;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.okJson;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.client.WireMock.urlPathEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.options;
import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RestAssuredCapabilitiesTest {
    @Test
    void requestCompositionExtractionAndTelemetryRemainComposable() {
        WireMockServer server = new WireMockServer(options().dynamicPort());
        server.start();
        try {
            server.stubFor(get(urlPathEqualTo("/posts/42"))
                    .withQueryParam("mode", equalTo("strict"))
                    .willReturn(okJson("""
                            {"userId":7,"id":42,"title":"composed-contract","body":"fixture"}
                            """).withHeader("X-Contract-Version", "v1")));

            TestConfig config = new TestConfig(URI.create(server.baseUrl()), 1_000, 2_000, "composition");
            ContractTelemetryFilter telemetry = new ContractTelemetryFilter();

            String title = given()
                    .spec(ApiSpecs.request(config))
                    .filter(telemetry)
                    .queryParam("mode", "strict")
                    .pathParam("id", 42)
                    .when()
                    .get("/posts/{id}")
                    .then()
                    .spec(ApiSpecs.jsonResponse())
                    .statusCode(200)
                    .header("X-Contract-Version", "v1")
                    .body("id", org.hamcrest.Matchers.equalTo(42))
                    .extract()
                    .path("title");

            var observation = telemetry.observations().get(0);
            assertAll(
                    () -> assertEquals("composed-contract", title),
                    () -> assertEquals("GET", observation.method()),
                    () -> assertEquals("/posts/42", observation.path()),
                    () -> assertEquals(200, observation.statusCode()),
                    () -> assertTrue(observation.durationMs() >= 0));
        } finally {
            server.stop();
        }
    }

    @Test
    void cookieFilterPersistsServerStateAcrossRequests() {
        WireMockServer server = new WireMockServer(options().dynamicPort());
        server.start();
        try {
            server.stubFor(post(urlEqualTo("/session"))
                    .willReturn(aResponse()
                            .withStatus(201)
                            .withHeader("Content-Type", "application/json")
                            .withHeader("Set-Cookie", "fixture-session=active; Path=/; HttpOnly")
                            .withBody("{\"authenticated\":true}")));
            server.stubFor(get(urlEqualTo("/session/me"))
                    .withCookie("fixture-session", equalTo("active"))
                    .willReturn(okJson("{\"authenticated\":true}")));

            TestConfig config = new TestConfig(URI.create(server.baseUrl()), 1_000, 2_000, "cookie-state");
            CookieFilter cookies = new CookieFilter();

            given()
                    .spec(ApiSpecs.request(config))
                    .filter(cookies)
                    .when()
                    .post("/session")
                    .then()
                    .spec(ApiSpecs.jsonResponse())
                    .statusCode(201)
                    .body("authenticated", org.hamcrest.Matchers.equalTo(true));

            given()
                    .spec(ApiSpecs.request(config))
                    .filter(cookies)
                    .when()
                    .get("/session/me")
                    .then()
                    .spec(ApiSpecs.jsonResponse())
                    .statusCode(200)
                    .body("authenticated", org.hamcrest.Matchers.equalTo(true));
        } finally {
            server.stop();
        }
    }
}
