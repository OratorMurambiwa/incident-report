package com.incidentiq.incident;

import com.incidentiq.common.ResourceNotFoundException;
import com.incidentiq.diagnosis.DiagnosisRepository;
import com.incidentiq.diagnosis.DiagnosisResponse;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class IncidentService {
    private final com.incidentiq.outbox.OutboxStore outbox;
    private final IncidentRepository incidents;
    private final DiagnosisRepository diagnoses;

    public IncidentService(IncidentRepository incidents, DiagnosisRepository diagnoses, com.incidentiq.outbox.OutboxStore outbox) {
        this.outbox = outbox;
        this.incidents = incidents;
        this.diagnoses = diagnoses;
    }

    @Transactional
    public IncidentResponse create(CreateIncidentRequest request) {
        Incident incident = new Incident(request.service(), request.title(), request.description(), request.severity());
        Incident saved = incidents.save(incident);
        incidents.flush();
        outbox.enqueue(saved);
        return IncidentResponse.from(saved);
    }

    public IncidentPage list(int page, int size) {
        var result = incidents.findAll(PageRequest.of(page, size,
                Sort.by(Sort.Direction.DESC, "createdAt", "id")));
        return new IncidentPage(result.map(IncidentResponse::from).getContent(),
                page, size, result.getTotalElements(), result.getTotalPages());
    }

    public IncidentPage listFiltered(int page, int size, Severity severity, IncidentStatus status, String service) {
        var result = incidents.search(severity, status, service == null || service.isBlank() ? null : service.strip(),
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt", "id")));
        return new IncidentPage(result.map(IncidentResponse::from).getContent(),
                page, size, result.getTotalElements(), result.getTotalPages());
    }

    public IncidentResponse get(UUID id) {
        return IncidentResponse.from(find(id));
    }

    public DiagnosisResponse diagnosis(UUID id) {
        find(id);
        return diagnoses.findByIncidentId(id).map(DiagnosisResponse::from)
                .orElseThrow(() -> new ResourceNotFoundException("Diagnosis not available for incident " + id));
    }

    private Incident find(UUID id) {
        return incidents.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Incident not found: " + id));
    }
}
