package com.example.testing;

import com.example.framework.TestConfig;
import com.github.tomakehurst.wiremock.WireMockServer;

import java.net.URI;

import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.okJson;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.options;

/**
 * Repository-owned HTTP fixture for REST Assured contracts.
 *
 * <p>The fixture deliberately owns transport availability while leaving request
 * construction and assertions to REST Assured tests. It binds an ephemeral
 * loopback port so parallel CI jobs never depend on a shared fixed service.</p>
 */
public final class PostsApiFixture implements AutoCloseable {
    private final WireMockServer server;

    public PostsApiFixture() {
        server = new WireMockServer(options().dynamicPort());
        server.start();
    }

    public static PostsApiFixture withHappyPath() {
        var fixture = new PostsApiFixture();
        fixture.stubHappyPath();
        return fixture;
    }

    public WireMockServer server() {
        return server;
    }

    public URI baseUri() {
        return URI.create(server.baseUrl());
    }

    public TestConfig config(String runId) {
        return new TestConfig(baseUri(), 1_000, 2_000, runId);
    }

    public void stubHappyPath() {
        server.stubFor(get(urlEqualTo("/posts"))
                .willReturn(okJson("""
                        [
                          {"userId":1,"id":1,"title":"fixture-post-1","body":"deterministic local fixture"},
                          {"userId":2,"id":2,"title":"fixture-post-2","body":"deterministic local fixture"}
                        ]
                        """)));
        server.stubFor(get(urlEqualTo("/posts/1"))
                .willReturn(okJson("""
                        {"userId":1,"id":1,"title":"fixture-post-1","body":"deterministic local fixture"}
                        """)));
    }

    @Override
    public void close() {
        if (server.isRunning()) {
            server.stop();
        }
    }
}
