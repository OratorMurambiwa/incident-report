package com.incidentiq.incident;

import java.time.Instant;
import java.util.UUID;

public record IncidentResponse(UUID id, String service, String title, String description,
        Severity severity, IncidentStatus status, Instant createdAt, Instant updatedAt) {
    public static IncidentResponse from(Incident incident) {
        return new IncidentResponse(incident.getId(), incident.getService(), incident.getTitle(),
                incident.getDescription(), incident.getSeverity(), incident.getStatus(),
                incident.getCreatedAt(), incident.getUpdatedAt());
    }
}
