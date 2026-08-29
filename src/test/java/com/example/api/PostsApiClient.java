package com.example.api;

import com.example.framework.ApiSpecs;
import com.example.framework.TestConfig;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;

import static io.restassured.RestAssured.given;

/**
 * Domain-focused REST Assured client for the posts resource.
 *
 * <p>The client is deliberately independent of any public API provider. Its
 * target is supplied through {@link TestConfig}, allowing required CI to use the
 * repository-owned WireMock fixture while environment integration remains an
 * explicit runtime choice.</p>
 */
public class PostsApiClient {
    private final RequestSpecification requestSpec;

    public PostsApiClient() {
        this(TestConfig.fromEnvironment());
    }

    public PostsApiClient(String baseUrl) {
        this(new TestConfig(
                java.net.URI.create(baseUrl),
                5_000,
                15_000,
                java.util.UUID.randomUUID().toString()));
    }

    public PostsApiClient(TestConfig config) {
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
