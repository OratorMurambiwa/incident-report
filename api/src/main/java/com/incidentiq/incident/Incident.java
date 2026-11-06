package com.incidentiq.incident;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "incidents")
public class Incident {
    @Id
    private UUID id;
    @Column(nullable = false, length = 100)
    private String service;
    @Column(nullable = false, length = 200)
    private String title;
    @Column(nullable = false, length = 10000)
    private String description;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private Severity severity;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private IncidentStatus status;
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected Incident() { }

    public Incident(String service, String title, String description, Severity severity) {
        this.id = UUID.randomUUID();
        this.service = service.strip();
        this.title = title.strip();
        this.description = description.strip();
        this.severity = severity;
        this.status = IncidentStatus.PENDING;
        this.createdAt = Instant.now().truncatedTo(java.time.temporal.ChronoUnit.MICROS);
        this.updatedAt = this.createdAt;
    }

    public UUID getId() { return id; }
    public String getService() { return service; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public Severity getSeverity() { return severity; }
    public IncidentStatus getStatus() { return status; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
