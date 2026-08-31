package com.example.db;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Provider-specific persistence contract against an isolated PostgreSQL
 * Testcontainers instance. Test-owned state is connection-scoped so reruns do
 * not depend on row ordering, pre-existing identifiers, or cleanup timing.
 */
@DisplayName("PostgreSQL integration contracts")
public class PostgresIntegrationTest {

    private static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16.15-alpine")
            .withDatabaseName("testdb")
            .withUsername("test")
            .withPassword("test");

    @BeforeAll
    static void startContainer() {
        postgres.start();
    }

    @AfterAll
    static void stopContainer() {
        postgres.stop();
    }

    @Test
    @DisplayName("Generated identity can be used to read the row that was written")
    void shouldPersistAndQueryTheOwnedRow() throws Exception {
        try (Connection connection = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())) {
            try (Statement statement = connection.createStatement()) {
                statement.execute("CREATE TEMP TABLE users (id BIGSERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL)");
            }

            long insertedId;
            try (PreparedStatement insert = connection.prepareStatement(
                    "INSERT INTO users(name) VALUES (?)",
                    Statement.RETURN_GENERATED_KEYS)) {
                insert.setString(1, "contract-user");
                assertEquals(1, insert.executeUpdate());

                try (ResultSet keys = insert.getGeneratedKeys()) {
                    assertTrue(keys.next(), "PostgreSQL should return the generated identity");
                    insertedId = keys.getLong(1);
                    assertFalse(keys.next(), "One insert must produce exactly one generated identity");
                }
            }

            try (PreparedStatement select = connection.prepareStatement(
                    "SELECT name FROM users WHERE id = ?")) {
                select.setLong(1, insertedId);
                try (ResultSet result = select.executeQuery()) {
                    assertTrue(result.next(), "The inserted row should be queryable by its generated identity");
                    assertEquals("contract-user", result.getString("name"));
                    assertFalse(result.next(), "The generated identity should identify exactly one row");
                }
            }
        }
    }
}
