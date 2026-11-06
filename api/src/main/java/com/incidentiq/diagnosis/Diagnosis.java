package com.incidentiq.diagnosis;

import com.incidentiq.incident.Incident;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

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
}
