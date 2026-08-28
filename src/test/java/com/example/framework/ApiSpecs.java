package com.example.framework;

import io.restassured.builder.RequestSpecBuilder;
import io.restassured.builder.ResponseSpecBuilder;
import io.restassured.config.HttpClientConfig;
import io.restassured.config.RestAssuredConfig;
import io.restassured.http.ContentType;
import io.restassured.specification.RequestSpecification;
import io.restassured.specification.ResponseSpecification;

public final class ApiSpecs {
    private ApiSpecs() {}

    public static RequestSpecification request(TestConfig config) {
        var httpConfig = HttpClientConfig.httpClientConfig()
                .setParam("http.connection.timeout", config.connectTimeoutMs())
                .setParam("http.socket.timeout", config.readTimeoutMs());

        return new RequestSpecBuilder()
                .setBaseUri(config.baseUri().toString())
                .setAccept(ContentType.JSON)
                .addHeader("X-Test-Run-Id", config.runId())
                .setConfig(RestAssuredConfig.config().httpClient(httpConfig))
                .build();
    }

    public static ResponseSpecification jsonResponse() {
        return new ResponseSpecBuilder()
                .expectContentType(ContentType.JSON)
                .build();
    }
}
