package com.incidentiq.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.incidentiq.incident.Incident;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class OutboxStore {
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public OutboxStore(JdbcTemplate jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    public void enqueue(Incident incident) {
        UUID eventId = UUID.randomUUID();
        var event = new IncidentCreatedEvent(1, eventId, incident.getId(), incident.getService(),
                incident.getTitle(), incident.getDescription(), incident.getSeverity(), incident.getCreatedAt());
        try {
            jdbc.update("""
                    INSERT INTO incidentiq_api.outbox_events (event_id, incident_id, topic, payload)
                    VALUES (?, ?, 'incident.created', ?::jsonb)
                    """, eventId, incident.getId(), json.writeValueAsString(event));
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Cannot serialize incident event", exception);
        }
    }

    public Optional<PendingEvent> lockNext() {
        return jdbc.query("""
                SELECT event_id, incident_id, topic, payload::text, attempts
                FROM incidentiq_api.outbox_events
                WHERE published_at IS NULL AND next_attempt_at <= now()
                ORDER BY created_at, event_id LIMIT 1 FOR UPDATE SKIP LOCKED
                """, (row, index) -> new PendingEvent(row.getObject(1, UUID.class),
                row.getObject(2, UUID.class), row.getString(3), row.getString(4), row.getInt(5)))
                .stream().findFirst();
    }

    public void published(UUID id) {
        jdbc.update("""
                UPDATE incidentiq_api.outbox_events
                SET published_at = now(), attempts = attempts + 1, last_error = NULL WHERE event_id = ?
                """, id);
    }

    public void retry(PendingEvent event, String error) {
        long seconds = Math.min(300, 1L << Math.min(event.attempts() + 1, 8));
        jdbc.update("""
                UPDATE incidentiq_api.outbox_events
                SET attempts = attempts + 1, last_error = ?, next_attempt_at = ? WHERE event_id = ?
                """, error, java.sql.Timestamp.from(Instant.now().plusSeconds(seconds)), event.eventId());
    }

    public record PendingEvent(UUID eventId, UUID incidentId, String topic, String payload, int attempts) { }
}
