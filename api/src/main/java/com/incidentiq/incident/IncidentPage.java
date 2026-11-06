package com.incidentiq.incident;

import java.util.List;

public record IncidentPage(List<IncidentResponse> content, int page, int size,
        long totalElements, int totalPages) { }
