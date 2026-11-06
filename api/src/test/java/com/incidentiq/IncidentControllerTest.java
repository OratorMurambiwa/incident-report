package com.incidentiq;

import com.incidentiq.common.ResourceNotFoundException;
import com.incidentiq.incident.*;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(IncidentController.class)
class IncidentControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean IncidentService service;

    @Test
    void createsIncidentWithLocationAndPendingStatus() throws Exception {
        var response = IncidentResponse.from(new Incident("billing", "Timeout", "Requests time out", Severity.HIGH));
        when(service.create(any())).thenReturn(response);
        mvc.perform(post("/api/incidents").contentType(MediaType.APPLICATION_JSON).content("""
                {"service":"billing","title":"Timeout","description":"Requests time out","severity":"HIGH"}
                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/incidents/" + response.id()))
                .andExpect(jsonPath("$.id").value(response.id().toString()))
                .andExpect(jsonPath("$.status").value("PENDING"));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "{}",
        "{\"service\":\" \",\"title\":\"t\",\"description\":\"d\",\"severity\":\"LOW\"}",
        "{\"service\":\"s\",\"title\":\"\",\"description\":\"d\",\"severity\":\"LOW\"}",
        "{\"service\":\"s\",\"title\":\"t\",\"description\":\" \",\"severity\":\"LOW\"}",
        "{\"service\":\"s\",\"title\":\"t\",\"description\":\"d\",\"severity\":null}"
    })
    void rejectsInvalidFields(String body) throws Exception {
        mvc.perform(post("/api/incidents").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors").isMap());
        verifyNoInteractions(service);
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "{\"severity\":\"URGENT\"}",
        "{\"status\":\"RESOLVED\"}",
        "{invalid"
    })
    void rejectsMalformedInput(String body) throws Exception {
        mvc.perform(post("/api/incidents").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @Test
    void rejectsOversizedTitle() throws Exception {
        String body = "{\"service\":\"s\",\"title\":\"" + "t".repeat(201)
                + "\",\"description\":\"d\",\"severity\":\"LOW\"}";
        mvc.perform(post("/api/incidents").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.title").exists());
        verifyNoInteractions(service);
    }

    @Test
    void missingIncidentReturns404() throws Exception {
        UUID id = UUID.randomUUID();
        when(service.get(id)).thenThrow(new ResourceNotFoundException("Incident not found: " + id));
        mvc.perform(get("/api/incidents/" + id)).andExpect(status().isNotFound());
    }

    @Test
    void missingDiagnosisReturns404() throws Exception {
        UUID id = UUID.randomUUID();
        when(service.diagnosis(id)).thenThrow(new ResourceNotFoundException("Diagnosis not available"));
        mvc.perform(get("/api/incidents/" + id + "/diagnosis")).andExpect(status().isNotFound());
    }

    @Test
    void listsIncidents() throws Exception {
        when(service.list(0, 20)).thenReturn(new IncidentPage(List.of(), 0, 20, 0, 0));
        mvc.perform(get("/api/incidents")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isEmpty());
    }

    @ParameterizedTest
    @ValueSource(strings = {"/api/incidents/not-a-uuid", "/api/incidents?page=-1", "/api/incidents?size=101", "/api/incidents?size=0"})
    void rejectsInvalidPathAndPagination(String path) throws Exception {
        mvc.perform(get(path)).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }
}
