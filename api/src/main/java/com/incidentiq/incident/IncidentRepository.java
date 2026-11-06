package com.incidentiq.incident;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentRepository extends JpaRepository<Incident, UUID> {
    @org.springframework.data.jpa.repository.Query("""
            SELECT i FROM Incident i WHERE (:severity IS NULL OR i.severity = :severity)
              AND (:status IS NULL OR i.status = :status)
              AND (:service IS NULL OR locate(lower(:service), lower(i.service)) > 0)
            """)
    org.springframework.data.domain.Page<Incident> search(
            @org.springframework.data.repository.query.Param("severity") Severity severity,
            @org.springframework.data.repository.query.Param("status") IncidentStatus status,
            @org.springframework.data.repository.query.Param("service") String service,
            org.springframework.data.domain.Pageable pageable);
}
