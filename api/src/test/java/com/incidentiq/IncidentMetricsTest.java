package com.incidentiq;

import com.incidentiq.metrics.IncidentMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class IncidentMetricsTest {
    @Test
    void gaugesReadCurrentPersistedCountsRatherThanProcessCounters() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents", Long.class))
                .thenReturn(7L, 8L);
        when(jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents WHERE status = ?", Long.class, "PENDING"))
                .thenReturn(2L);
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        try {
            new IncidentMetrics(jdbc).bindTo(registry);
            assertEquals(7.0, registry.get("incidentiq.incidents").gauge().value());
            assertEquals(8.0, registry.get("incidentiq.incidents").gauge().value());
            assertEquals(2.0, registry.get("incidentiq.incidents.by.status").tag("status", "PENDING").gauge().value());
            assertEquals(7, registry.getMeters().size()); // one total + six enum states
        } finally {
            registry.close();
        }
    }

    @Test
    void databaseUnavailabilityProducesMissingDataInsteadOfFalseZero() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents", Long.class))
                .thenThrow(new DataAccessResourceFailureException("database unavailable"));
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        try {
            new IncidentMetrics(jdbc).bindTo(registry);
            assertTrue(Double.isNaN(registry.get("incidentiq.incidents").gauge().value()));
        } finally {
            registry.close();
        }
    }
}
