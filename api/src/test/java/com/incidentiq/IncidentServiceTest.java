package com.incidentiq;

import com.incidentiq.common.ResourceNotFoundException;
import com.incidentiq.diagnosis.DiagnosisRepository;
import com.incidentiq.incident.*;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class IncidentServiceTest {
    @Mock com.incidentiq.outbox.OutboxStore outbox;
    @Mock IncidentRepository incidents;
    @Mock DiagnosisRepository diagnoses;

    @Test
    void creationPersistsPendingIncidentWithUuidAndTimestamps() {
        when(incidents.save(any())).thenAnswer(call -> call.getArgument(0));
        var result = new IncidentService(incidents, diagnoses, outbox).create(
                new CreateIncidentRequest(" billing ", " Timeout ", " Details ", Severity.HIGH));
        assertNotNull(result.id());
        assertEquals("billing", result.service());
        assertEquals(IncidentStatus.PENDING, result.status());
        assertNotNull(result.createdAt());
        assertEquals(result.createdAt(), result.updatedAt());
        verify(incidents).save(any(Incident.class));
        verify(outbox).enqueue(any(Incident.class));
    }

    @Test
    void missingIncidentThrowsNotFound() {
        UUID id = UUID.randomUUID();
        when(incidents.findById(id)).thenReturn(Optional.empty());
        assertThrows(ResourceNotFoundException.class, () -> new IncidentService(incidents, diagnoses, outbox).get(id));
    }

    @Test
    void diagnosisChecksIncidentExists() {
        UUID id = UUID.randomUUID();
        when(incidents.findById(id)).thenReturn(Optional.empty());
        assertThrows(ResourceNotFoundException.class, () -> new IncidentService(incidents, diagnoses, outbox).diagnosis(id));
        verifyNoInteractions(diagnoses);
    }

    @Test
    void existingIncidentWithoutDiagnosisThrowsNotFound() {
        Incident incident = new Incident("s", "t", "d", Severity.LOW);
        when(incidents.findById(incident.getId())).thenReturn(Optional.of(incident));
        when(diagnoses.findByIncidentId(incident.getId())).thenReturn(Optional.empty());
        assertThrows(ResourceNotFoundException.class,
                () -> new IncidentService(incidents, diagnoses, outbox).diagnosis(incident.getId()));
    }
}
