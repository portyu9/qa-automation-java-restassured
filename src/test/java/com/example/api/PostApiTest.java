package com.example.api;

import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * End-to-end API contracts for the configured posts service. Assertions combine
 * protocol behavior, semantic values, and version-controlled JSON Schemas.
 */
@DisplayName("Posts API contracts")
public class PostApiTest {
    private final JsonPlaceholderClient client = new JsonPlaceholderClient();

    @Test
    @DisplayName("List posts with the expected protocol and resource schema")
    void shouldReturnListOfPosts() {
        Response response = client.getPosts();

        response.then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("size()", greaterThan(0))
                .body("[0].id", greaterThan(0))
                .body("[0].userId", greaterThan(0))
                .body("[0].title", not(emptyOrNullString()))
                .body("[0].body", not(emptyOrNullString()));

        assertThat(
                "posts response should match the collection schema",
                response.getBody().asString(),
                matchesJsonSchemaInClasspath("post-schema.json"));
    }

    @Test
    @DisplayName("Retrieve one post by a validated identifier")
    void shouldReturnSinglePost() {
        int postId = 1;
        Response response = client.getPost(postId);

        response.then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("id", equalTo(postId))
                .body("userId", greaterThan(0))
                .body("title", not(emptyOrNullString()))
                .body("body", not(emptyOrNullString()));

        assertThat(
                "single post response should match the resource schema",
                response.getBody().asString(),
                matchesJsonSchemaInClasspath("single-post-schema.json"));
    }
}
