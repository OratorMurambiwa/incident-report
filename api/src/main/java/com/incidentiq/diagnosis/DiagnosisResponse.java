package com.incidentiq.diagnosis;

import java.time.Instant;
import java.util.UUID;

public record DiagnosisResponse(UUID id, UUID incidentId, String summary,
        String recommendations, Instant createdAt, Instant updatedAt) {
    public static DiagnosisResponse from(Diagnosis diagnosis) {
        return new DiagnosisResponse(diagnosis.getId(), diagnosis.getIncident().getId(),
                diagnosis.getSummary(), diagnosis.getRecommendations(),
                diagnosis.getCreatedAt(), diagnosis.getUpdatedAt());
    }
}
