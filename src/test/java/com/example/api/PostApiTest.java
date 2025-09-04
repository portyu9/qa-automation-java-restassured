package com.example.api;

import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.*;

/**
 * End‑to‑end tests for the JSONPlaceholder posts resource.  
 *
 * I deliberately keep the assertions expressive and descriptive using
 * Hamcrest matchers. The schema file `post-schema.json` resides in
 * `src/test/resources` and is automatically resolved from the classpath.
 */
@DisplayName("JSONPlaceholder API Tests")
public class PostApiTest {

    private final JsonPlaceholderClient client = new JsonPlaceholderClient();

    @Test
    @DisplayName("Verify /posts returns a list of posts with expected structure")
    void shouldReturnListOfPosts() {
        Response response = client.getPosts();

        // Basic status and header assertions
        response.then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("size()", greaterThan(0))
                .body("[0].id", notNullValue())
                .body("[0].userId", notNullValue())
                .body("[0].title", notNullValue())
                .body("[0].body", notNullValue());

        // Validate the JSON schema located in src/test/resources/post-schema.json
        assertThat("Response should match the posts schema",
                response.getBody().asString(), matchesJsonSchemaInClasspath("post-schema.json"));
    }

    @Test
    @DisplayName("Verify a single post can be retrieved by ID")
    void shouldReturnSinglePost() {
        int postId = 1;
        Response response = client.getPost(postId);

        response.then()
                .statusCode(200)
                .contentType(ContentType.JSON)
                .body("id", equalTo(postId))
                .body("userId", notNullValue())
                .body("title", notNullValue())
                .body("body", notNullValue());
    }
}
