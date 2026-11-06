package com.incidentiq.diagnosis;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record DiagnosisResponse(UUID id, UUID incidentId, String summary,
        String recommendations, Instant createdAt, Instant updatedAt,
        String mode, String provider, String model, UUID eventId,
        List<Diagnosis.CitedStatement> likelyCauses, List<Diagnosis.CitedStatement> investigationSteps,
        List<Diagnosis.CitedStatement> suggestedRemediation, List<String> citedRunbooks,
        List<Diagnosis.Evidence> retrievedEvidence, String uncertainty) {
    public static DiagnosisResponse from(Diagnosis diagnosis) {
        return new DiagnosisResponse(diagnosis.getId(), diagnosis.getIncident().getId(),
                diagnosis.getSummary(), diagnosis.getRecommendations(),
                diagnosis.getCreatedAt(), diagnosis.getUpdatedAt(), diagnosis.getMode(),
                diagnosis.getProvider(), diagnosis.getModel(), diagnosis.getEventId(),
                diagnosis.getLikelyCauses(), diagnosis.getInvestigationSteps(),
                diagnosis.getSuggestedRemediation(), diagnosis.getCitedRunbooks(),
                diagnosis.getRetrievedEvidence(), diagnosis.getUncertainty());
    }
}
