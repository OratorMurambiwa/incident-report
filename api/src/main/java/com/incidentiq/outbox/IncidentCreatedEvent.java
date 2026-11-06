package com.incidentiq.outbox;

import com.incidentiq.incident.Severity;
import java.time.Instant;
import java.util.UUID;

public record IncidentCreatedEvent(int schemaVersion, UUID eventId, UUID incidentId, String service,
        String title, String description, Severity severity, Instant timestamp) { }
