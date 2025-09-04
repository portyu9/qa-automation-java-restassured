package com.example.api;

import io.restassured.response.Response;

import static io.restassured.RestAssured.given;

/**
 * Simple API client abstraction for JSONPlaceholder.  
 *
 * I created this class following a Page Object–style pattern so that my tests
 * interact with a single abstraction rather than directly invoking RestAssured.  
 * This makes the tests easier to read and maintain because all endpoint
 * configuration lives in one place.  
 */
public class JsonPlaceholderClient {
    private final String baseUrl;

    /**
     * Construct a client pointing at the default JSONPlaceholder base URL.
     */
    public JsonPlaceholderClient() {
        this("https://jsonplaceholder.typicode.com");
    }

    /**
     * Construct a client with a custom base URL.  
     * Useful when pointing to a stub or mock server.
     *
     * @param baseUrl base URL of the JSONPlaceholder API
     */
    public JsonPlaceholderClient(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    /**
     * Retrieve all posts.
     *
     * @return the HTTP response
     */
    public Response getPosts() {
        return given()
                .baseUri(baseUrl)
                .when()
                .get("/posts")
                .then()
                .extract()
                .response();
    }

    /**
     * Retrieve a single post by ID.
     *
     * @param id post identifier
     * @return the HTTP response
     */
    public Response getPost(int id) {
        return given()
                .baseUri(baseUrl)
                .pathParam("id", id)
                .when()
                .get("/posts/{id}")
                .then()
                .extract()
                .response();
    }
}
