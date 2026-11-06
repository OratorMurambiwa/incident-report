package com.incidentiq.diagnosis;

import com.incidentiq.incident.Incident;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import java.util.List;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "diagnoses")
public class Diagnosis {
    @Id
    private UUID id;
    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "incident_id", nullable = false, unique = true)
    private Incident incident;
    @Column(nullable = false, length = 10000)
    private String summary;
    @Column(nullable = false, length = 20000)
    private String recommendations;
    @Column(nullable = false, length = 24)
    private String mode;
    @Column(nullable = false, length = 16)
    private String provider;
    private String model;
    @Column(name = "event_id")
    private UUID eventId;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "likely_causes", nullable = false, columnDefinition = "jsonb")
    private List<CitedStatement> likelyCauses;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "investigation_steps", nullable = false, columnDefinition = "jsonb")
    private List<CitedStatement> investigationSteps;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "suggested_remediation", nullable = false, columnDefinition = "jsonb")
    private List<CitedStatement> suggestedRemediation;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "cited_runbooks", nullable = false, columnDefinition = "jsonb")
    private List<String> citedRunbooks;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "retrieved_evidence", nullable = false, columnDefinition = "jsonb")
    private List<Evidence> retrievedEvidence;
    @Column(nullable = false, columnDefinition = "text")
    private String uncertainty;
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Diagnosis() { }

    public UUID getId() { return id; }
    public Incident getIncident() { return incident; }
    public String getSummary() { return summary; }
    public String getRecommendations() { return recommendations; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public String getMode() { return mode; }
    public String getProvider() { return provider; }
    public String getModel() { return model; }
    public UUID getEventId() { return eventId; }
    public List<CitedStatement> getLikelyCauses() { return likelyCauses; }
    public List<CitedStatement> getInvestigationSteps() { return investigationSteps; }
    public List<CitedStatement> getSuggestedRemediation() { return suggestedRemediation; }
    public List<String> getCitedRunbooks() { return citedRunbooks; }
    public List<Evidence> getRetrievedEvidence() { return retrievedEvidence; }
    public String getUncertainty() { return uncertainty; }

    public record CitedStatement(String text, List<String> sources) { }
    public record Evidence(UUID chunkId, String source, double similarity, String excerpt) { }
}
