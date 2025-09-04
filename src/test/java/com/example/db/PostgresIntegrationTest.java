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

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Integration tests against a real PostgreSQL instance using Testcontainers.  
 *
 * I spin up a lightweight PostgreSQL container before all tests and tear it down afterwards.  
 * The test demonstrates creating a table, inserting a row and verifying the persisted data using JDBC.
 */
@DisplayName("PostgreSQL Integration Tests")
public class PostgresIntegrationTest {

    private static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
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
    @DisplayName("Persisting and querying data works")
    void shouldPersistAndQueryData() throws Exception {
        try (Connection conn = DriverManager.getConnection(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())) {
            // Create table if not exists
            conn.createStatement().execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(50));");
            // Insert a row
            try (PreparedStatement stmt = conn.prepareStatement("INSERT INTO users(name) VALUES (?)", PreparedStatement.RETURN_GENERATED_KEYS)) {
                stmt.setString(1, "Alice");
                stmt.executeUpdate();
            }
            // Query data
            try (ResultSet rs = conn.createStatement().executeQuery("SELECT name FROM users WHERE id = 1;")) {
                rs.next();
                String name = rs.getString("name");
                assertEquals("Alice", name, "The retrieved name should match the inserted value.");
            }
        }
    }
}
