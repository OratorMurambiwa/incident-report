package com.incidentiq;

import com.incidentiq.incident.*;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
@EnabledIfEnvironmentVariable(named = "RUN_DATABASE_TESTS", matches = "true")
class PostgresIntegrationTest {
    @Autowired IncidentService service;
    @Autowired IncidentRepository incidents;
    @Autowired JdbcTemplate jdbc;
    @Autowired MockMvc mvc;

    @Test
    void persistsAndReadsIncident() {
        var created = service.create(new CreateIncidentRequest("db-test", "Timeout", "Details", Severity.CRITICAL));
        incidents.flush();
        assertEquals(created, service.get(created.id()));
        assertEquals(IncidentStatus.PENDING, created.status());
        assertTrue(service.list(0, 20).content().stream().anyMatch(i -> i.id().equals(created.id())));
    }

    @Test
    void returnsPersistedDiagnosis() throws Exception {
        var incident = service.create(new CreateIncidentRequest("db-test", "Timeout", "Details", Severity.HIGH));
        incidents.flush();
        UUID diagnosis = UUID.randomUUID();
        jdbc.update("INSERT INTO incidentiq_api.diagnoses (id, incident_id, summary, recommendations) VALUES (?, ?, ?, ?)",
                diagnosis, incident.id(), "Database connection exhaustion", "Inspect connection pool metrics");
        mvc.perform(get("/api/incidents/" + incident.id() + "/diagnosis"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(diagnosis.toString()))
                .andExpect(jsonPath("$.incidentId").value(incident.id().toString()));
    }

    @Test
    void rejectsOrphanDiagnosis() {
        assertThrows(DataIntegrityViolationException.class, () -> jdbc.update(
                "INSERT INTO incidentiq_api.diagnoses (id, incident_id, summary, recommendations) VALUES (?, ?, ?, ?)",
                UUID.randomUUID(), UUID.randomUUID(), "Summary", "Recommendation"));
    }

    @Test
    void rejectsInvalidSeverityInDatabase() {
        assertThrows(DataIntegrityViolationException.class, () -> jdbc.update(
                "INSERT INTO incidentiq_api.incidents (id, service, title, description, severity) VALUES (?, ?, ?, ?, ?)",
                UUID.randomUUID(), "s", "t", "d", "INVALID"));
    }

    @Test
    void rejectsMultipleDiagnosesForOneIncident() {
        var incident = service.create(new CreateIncidentRequest("db-test", "Timeout", "Details", Severity.HIGH));
        incidents.flush();
        String sql = "INSERT INTO incidentiq_api.diagnoses (id, incident_id, summary, recommendations) VALUES (?, ?, ?, ?)";
        jdbc.update(sql, UUID.randomUUID(), incident.id(), "First", "Check metrics");
        assertThrows(DataIntegrityViolationException.class,
                () -> jdbc.update(sql, UUID.randomUUID(), incident.id(), "Second", "Check logs"));
    }
}
