package com.incidentiq.diagnosis;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DiagnosisRepository extends JpaRepository<Diagnosis, UUID> {
    Optional<Diagnosis> findByIncidentId(UUID incidentId);
}
