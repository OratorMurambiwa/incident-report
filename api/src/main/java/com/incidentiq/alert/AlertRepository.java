package com.incidentiq.alert;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AlertRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public AlertRepository(JdbcTemplate jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    public State lock(String fingerprint) {
        jdbc.update("INSERT INTO incidentiq_api.alert_states (fingerprint) VALUES (?) ON CONFLICT DO NOTHING", fingerprint);
        jdbc.update("UPDATE incidentiq_api.alert_states SET updated_at = now() WHERE fingerprint = ?", fingerprint);
        return jdbc.queryForObject("""
                SELECT active_incident_id, active_starts_at, resolved_through
                FROM incidentiq_api.alert_states WHERE fingerprint = ? FOR UPDATE
                """, (row, index) -> new State(row.getObject(1, UUID.class), instant(row.getTimestamp(2)), instant(row.getTimestamp(3))), fingerprint);
    }

    public void activate(String fingerprint, UUID incidentId, AlertmanagerNotification.Alert alert) {
        jdbc.update("""
                INSERT INTO incidentiq_api.alert_incidents (incident_id, fingerprint, starts_at, labels, annotations)
                VALUES (?, ?, ?, ?::jsonb, ?::jsonb)
                """, incidentId, fingerprint, Timestamp.from(alert.startsAt()), encode(alert.labels()), encode(alert.annotations()));
        jdbc.update("""
                UPDATE incidentiq_api.alert_states SET active_incident_id = ?, active_starts_at = ?, updated_at = now()
                WHERE fingerprint = ?
                """, incidentId, Timestamp.from(alert.startsAt()), fingerprint);
    }

    public void advanceStart(String fingerprint, Instant startsAt) {
        jdbc.update("UPDATE incidentiq_api.alert_states SET active_starts_at = ?, updated_at = now() WHERE fingerprint = ?",
                Timestamp.from(startsAt), fingerprint);
    }

    public void resolve(String fingerprint, UUID incidentId, Instant endsAt) {
        if (incidentId != null) {
            jdbc.update("UPDATE incidentiq_api.incidents SET status = 'RESOLVED', updated_at = GREATEST(now(), updated_at) WHERE id = ?", incidentId);
            jdbc.update("UPDATE incidentiq_api.alert_incidents SET resolved_at = ? WHERE incident_id = ?", Timestamp.from(endsAt), incidentId);
        }
        jdbc.update("""
                UPDATE incidentiq_api.alert_states SET active_incident_id = NULL, active_starts_at = NULL,
                resolved_through = GREATEST(resolved_through, ?), updated_at = now() WHERE fingerprint = ?
                """, Timestamp.from(endsAt), fingerprint);
    }

    private String encode(Object value) {
        try { return json.writeValueAsString(value); }
        catch (JsonProcessingException exception) { throw new IllegalStateException("Cannot encode alert metadata", exception); }
    }

    private static Instant instant(Timestamp timestamp) { return timestamp == null ? null : timestamp.toInstant(); }
    public record State(UUID incidentId, Instant startsAt, Instant resolvedThrough) { }
}
