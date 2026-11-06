package com.incidentiq.metrics;

import io.micrometer.core.instrument.config.MeterFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MetricsConfiguration {
    @Bean
    public MeterFilter boundedHttpUriTags() {
        // MVC normally supplies URI templates; this cap also protects accidental raw-path tags.
        return MeterFilter.maximumAllowableTags("http.server.requests", "uri", 32, MeterFilter.deny());
    }
}
