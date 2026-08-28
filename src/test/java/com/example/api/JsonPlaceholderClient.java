package com.example.api;

import com.example.framework.ApiSpecs;
import com.example.framework.TestConfig;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;

import static io.restassured.RestAssured.given;

public class JsonPlaceholderClient {
    private final RequestSpecification requestSpec;

    public JsonPlaceholderClient() {
        this(TestConfig.fromEnvironment());
    }

    public JsonPlaceholderClient(String baseUrl) {
        this(new TestConfig(
                java.net.URI.create(baseUrl),
                5_000,
                15_000,
                java.util.UUID.randomUUID().toString()));
    }

    public JsonPlaceholderClient(TestConfig config) {
        this.requestSpec = ApiSpecs.request(config);
    }

    public Response getPosts() {
        return given()
                .spec(requestSpec)
                .when()
                .get("/posts")
                .then()
                .spec(ApiSpecs.jsonResponse())
                .extract().response();
    }

    public Response getPost(int id) {
        if (id <= 0) throw new IllegalArgumentException("id must be positive");
        return given()
                .spec(requestSpec)
                .pathParam("id", id)
                .when()
                .get("/posts/{id}")
                .then()
                .spec(ApiSpecs.jsonResponse())
                .extract().response();
    }
}
