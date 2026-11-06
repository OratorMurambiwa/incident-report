package com.incidentiq.metrics;

import com.incidentiq.incident.IncidentStatus;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.MeterBinder;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/** Database-backed gauges survive application restarts and never label individual incidents. */
@Component
public class IncidentMetrics implements MeterBinder {
    private final JdbcTemplate jdbc;

    public IncidentMetrics(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Override
    public void bindTo(MeterRegistry registry) {
        Gauge.builder("incidentiq.incidents", this, metrics -> metrics.count(null))
                .description("Current persisted incident total").register(registry);
        for (IncidentStatus status : IncidentStatus.values()) {
            Gauge.builder("incidentiq.incidents.by.status", this, metrics -> metrics.count(status))
                    .tag("status", status.name())
                    .description("Current persisted incidents by bounded status enum").register(registry);
        }
    }

    private double count(IncidentStatus status) {
        try {
            Long count = status == null
                    ? jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents", Long.class)
                    : jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents WHERE status = ?",
                            Long.class, status.name());
            return count == null ? Double.NaN : count.doubleValue();
        } catch (DataAccessException exception) {
            // Missing data is not zero incidents. Health checks separately report database outages.
            return Double.NaN;
        }
    }
}
