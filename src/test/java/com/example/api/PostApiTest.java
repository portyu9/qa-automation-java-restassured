package com.example.api;

import com.example.testing.PostsApiFixture;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * End-to-end HTTP contracts for the posts client against a repository-owned
 * WireMock service. Assertions combine protocol behavior, semantic values, and
 * version-controlled JSON Schemas without coupling required CI to a public API.
 */
@DisplayName("Posts API contracts")
public class PostApiTest {
    private PostsApiFixture fixture;
    private PostsApiClient client;

    @BeforeEach
    void startFixture() {
        fixture = PostsApiFixture.withHappyPath();
        client = new PostsApiClient(fixture.config("posts-api-contract"));
    }

    @AfterEach
    void stopFixture() {
        if (fixture != null) fixture.close();
    }

    @Test
    @DisplayName("List posts with the expected protocol and resource schema")
    void shouldReturnListOfPosts() {
        Response response = client.getPosts();

        response.then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("size()", equalTo(2))
                .body("[0].id", equalTo(1))
                .body("[0].userId", equalTo(1))
                .body("[0].title", equalTo("fixture-post-1"))
                .body("[0].body", equalTo("deterministic local fixture"));

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
                .body("userId", equalTo(1))
                .body("title", equalTo("fixture-post-1"))
                .body("body", equalTo("deterministic local fixture"));

        assertThat(
                "single post response should match the resource schema",
                response.getBody().asString(),
                matchesJsonSchemaInClasspath("single-post-schema.json"));
    }
}
