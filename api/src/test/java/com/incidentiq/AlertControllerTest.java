package com.incidentiq;

import com.incidentiq.alert.*;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AlertController.class)
class AlertControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean AlertService service;

    private static final String FIRING = """
        {"receiver":"incidentiq","status":"firing","version":"4","groupLabels":{"alertname":"Http500"},
         "alerts":[{"status":"firing","fingerprint":"abcdef0123456789","labels":{"alertname":"Http500","severity":"critical"},
         "annotations":{"summary":"HTTP 500 errors"},"startsAt":"2026-11-05T12:00:00Z","endsAt":"0001-01-01T00:00:00Z",
         "generatorURL":"http://prometheus:9090/graph"}],"truncatedAlerts":0}
        """;

    @Test
    void parsesRealAlertmanagerEnvelopeIncludingStandardExtraFields() throws Exception {
        when(service.accept(any())).thenReturn(new AlertReceipt(1, 0, 0, 0, List.of()));
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON).content(FIRING))
                .andExpect(status().isOk()).andExpect(jsonPath("$.created").value(1));
        verify(service).accept(argThat(notification -> notification.alerts().getFirst().status() == AlertmanagerNotification.Status.FIRING
                && notification.alerts().getFirst().fingerprint().equals("abcdef0123456789")));
    }

    @Test
    void perAlertResolvedStatusIsParsedEvenInFiringGroup() throws Exception {
        String resolved = FIRING.replace("\"status\":\"firing\",\"fingerprint\"", "\"status\":\"resolved\",\"fingerprint\"")
                .replace("0001-01-01T00:00:00Z", "2026-11-05T12:01:00Z");
        when(service.accept(any())).thenReturn(new AlertReceipt(0, 0, 1, 0, List.of()));
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON).content(resolved))
                .andExpect(status().isOk()).andExpect(jsonPath("$.resolved").value(1));
        verify(service).accept(argThat(notification -> notification.alerts().getFirst().status() == AlertmanagerNotification.Status.RESOLVED));
    }

    @ParameterizedTest
    @ValueSource(strings = {"{}", "{\"status\":\"firing\",\"alerts\":[]}", "{\"status\":\"unknown\",\"alerts\":[]}",
            "{\"status\":\"firing\",\"alerts\":[null]}", "{bad"})
    void rejectsInvalidEnvelope(String input) throws Exception {
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON).content(input)).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @Test
    void rejectsMissingFingerprint() throws Exception {
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON)
                .content(FIRING.replace("abcdef0123456789", "invalid"))).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @Test
    void rejectsMissingAlertName() throws Exception {
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON)
                .content(FIRING.replace("\"alertname\":\"Http500\",", ""))).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }

    @Test
    void rejectsInvalidResolutionTimestamp() throws Exception {
        String input = FIRING.replace("\"status\":\"firing\",\"fingerprint\"", "\"status\":\"resolved\",\"fingerprint\"");
        mvc.perform(post("/api/alerts/alertmanager").contentType(MediaType.APPLICATION_JSON).content(input)).andExpect(status().isBadRequest());
        verifyNoInteractions(service);
    }
}
