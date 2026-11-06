package com.incidentiq;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.incidentiq.incident.*;
import com.incidentiq.outbox.*;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@SpringBootTest
@EnabledIfEnvironmentVariable(named = "RUN_DATABASE_TESTS", matches = "true")
class OutboxPostgresTest {
    @Autowired IncidentService service;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @Autowired OutboxDelivery delivery;
    @Autowired PlatformTransactionManager manager;
    @MockitoBean KafkaTemplate<String, String> kafka;

    @Test
    void incidentAndEventRollbackTogether() {
        UUID[] id = new UUID[1];
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            id[0] = service.create(new CreateIncidentRequest("outbox-test", "Rollback", "Details", Severity.HIGH)).id();
            assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id = ?", Integer.class, id[0]));
            tx.setRollbackOnly();
        });
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents WHERE id = ?", Integer.class, id[0]));
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id = ?", Integer.class, id[0]));
    }

    @Test
    void persistsContractAndDurableRetryThenAcknowledges() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            var incident = service.create(new CreateIncidentRequest("outbox-test", "Retry", "Details", Severity.HIGH));
            var payload = jdbc.queryForObject("SELECT payload::text FROM incidentiq_api.outbox_events WHERE incident_id = ?", String.class, incident.id());
            try {
                var event = json.readTree(payload);
                assertEquals(1, event.get("schemaVersion").asInt());
                assertNotNull(UUID.fromString(event.get("eventId").asText()));
                assertEquals(incident.id().toString(), event.get("incidentId").asText());
                assertEquals("outbox-test", event.get("service").asText());
                assertEquals("Retry", event.get("title").asText());
                assertEquals("Details", event.get("description").asText());
                assertEquals("HIGH", event.get("severity").asText());
                assertNotNull(java.time.Instant.parse(event.get("timestamp").asText()));
            } catch (Exception exception) { throw new AssertionError(exception); }
            when(kafka.send(anyString(), anyString(), anyString()))
                    .thenReturn(CompletableFuture.failedFuture(new RuntimeException("offline")))
                    .thenReturn(CompletableFuture.completedFuture(null));
            assertTrue(delivery.publishNext());
            assertEquals(1, jdbc.queryForObject("SELECT attempts FROM incidentiq_api.outbox_events WHERE incident_id = ?", Integer.class, incident.id()));
            assertNull(jdbc.queryForObject("SELECT published_at FROM incidentiq_api.outbox_events WHERE incident_id = ?", java.sql.Timestamp.class, incident.id()));
            assertFalse(delivery.publishNext()); // backed off, not hot-looped
            jdbc.update("UPDATE incidentiq_api.outbox_events SET next_attempt_at = now() WHERE incident_id = ?", incident.id());
            assertTrue(delivery.publishNext());
            assertNotNull(jdbc.queryForObject("SELECT published_at FROM incidentiq_api.outbox_events WHERE incident_id = ?", java.sql.Timestamp.class, incident.id()));
            tx.setRollbackOnly();
        });
    }
}
