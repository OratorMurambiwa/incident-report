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
    void filtersAcrossAllPagesWithCombinedCriteria() throws Exception {
        String name = "Filter-" + UUID.randomUUID();
        var target = service.create(new CreateIncidentRequest(name, "Target", "Details", Severity.CRITICAL));
        service.create(new CreateIncidentRequest(name, "Other severity", "Details", Severity.LOW));
        service.create(new CreateIncidentRequest(name + "-extra", "Other status", "Details", Severity.CRITICAL));
        jdbc.update("UPDATE incidentiq_api.incidents SET status='RESOLVED' WHERE id <> ? AND service LIKE ?", target.id(), name + "%");
        mvc.perform(get("/api/incidents").param("severity", "CRITICAL").param("status", "PENDING")
                .param("service", name.toLowerCase()).param("size", "1"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.totalElements").value(1))
                .andExpect(jsonPath("$.content[0].id").value(target.id().toString()));
    }

    @Test
    void serviceFilterTreatsWildcardCharactersLiterally() {
        String name = UUID.randomUUID() + "%_";
        service.create(new CreateIncidentRequest(name, "Literal", "Details", Severity.HIGH));
        assertEquals(1, service.listFiltered(0, 20, null, null, name).totalElements());
        assertEquals(0, service.listFiltered(1, 1, null, null, name).content().size());
    }

    @Test
    void rejectsInvalidFilters() throws Exception {
        mvc.perform(get("/api/incidents").param("severity", "URGENT")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/incidents").param("status", "UNKNOWN")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/incidents").param("service", "x".repeat(101))).andExpect(status().isBadRequest());
    }

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
                .andExpect(jsonPath("$.incidentId").value(incident.id().toString()))
                .andExpect(jsonPath("$.mode").value("LEGACY"))
                .andExpect(jsonPath("$.likelyCauses").isEmpty());
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

    @Test
    void exposesStructuredGeneratedDiagnosis() throws Exception {
        var incident = service.create(new CreateIncidentRequest("db-test", "Timeout", "Details", Severity.HIGH));
        incidents.flush();
        UUID eventId = UUID.randomUUID();
        jdbc.update("INSERT INTO incidentiq_api.processed_events (event_id, incident_id, payload_hash) VALUES (?, ?, ?)",
                eventId, incident.id(), "a".repeat(64));
        jdbc.update("""
                INSERT INTO incidentiq_api.diagnoses
                (id, incident_id, summary, recommendations, mode, provider, model, event_id, likely_causes, cited_runbooks)
                VALUES (?, ?, ?, ?, 'GENERATED', 'ollama', 'test-model', ?, ?::jsonb, ?::jsonb)
                """, UUID.randomUUID(), incident.id(), "Possible pool exhaustion", "Review pool metrics", eventId,
                "[{\"text\":\"Possible pool exhaustion\",\"sources\":[\"database-failures.md\"]}]",
                "[\"database-failures.md\"]");
        mvc.perform(get("/api/incidents/" + incident.id() + "/diagnosis"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.mode").value("GENERATED"))
                .andExpect(jsonPath("$.provider").value("ollama"))
                .andExpect(jsonPath("$.model").value("test-model"))
                .andExpect(jsonPath("$.eventId").value(eventId.toString()))
                .andExpect(jsonPath("$.likelyCauses[0].sources[0]").value("database-failures.md"));
    }

    @Test
    void rejectsGeneratedDiagnosisWithoutProviderProvenance() {
        var incident = service.create(new CreateIncidentRequest("db-test", "Timeout", "Details", Severity.HIGH));
        incidents.flush();
        assertThrows(DataIntegrityViolationException.class, () -> jdbc.update(
                "INSERT INTO incidentiq_api.diagnoses (id, incident_id, summary, recommendations, mode) VALUES (?, ?, ?, ?, 'GENERATED')",
                UUID.randomUUID(), incident.id(), "Summary", "Recommendation"));
    }
}
