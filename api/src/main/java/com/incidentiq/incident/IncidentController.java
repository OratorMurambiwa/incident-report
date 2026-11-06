package com.incidentiq.incident;

import com.incidentiq.diagnosis.DiagnosisResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.net.URI;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/incidents")
public class IncidentController {
    private final IncidentService service;

    public IncidentController(IncidentService service) { this.service = service; }

    @PostMapping
    public ResponseEntity<IncidentResponse> create(@Valid @RequestBody CreateIncidentRequest request) {
        IncidentResponse response = service.create(request);
        return ResponseEntity.created(URI.create("/api/incidents/" + response.id())).body(response);
    }

    @GetMapping
    public IncidentPage list(@RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
            @RequestParam(required = false) Severity severity,
            @RequestParam(required = false) IncidentStatus status,
            @RequestParam(required = false) @jakarta.validation.constraints.Size(max = 100) String service) {
        return severity == null && status == null && service == null ? this.service.list(page, size)
                : this.service.listFiltered(page, size, severity, status, service);
    }

    @GetMapping("/{id}")
    public IncidentResponse get(@PathVariable UUID id) { return service.get(id); }

    @GetMapping("/{id}/diagnosis")
    public DiagnosisResponse diagnosis(@PathVariable UUID id) { return service.diagnosis(id); }
}
