package com.incidentiq.alert;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public record AlertmanagerNotification(
        @NotNull Status status,
        @NotEmpty @Size(max = 100) List<@NotNull @Valid Alert> alerts) {
    public enum Status {
        @JsonProperty("firing") FIRING,
        @JsonProperty("resolved") RESOLVED
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Alert(
            @NotNull Status status,
            @NotBlank @Pattern(regexp = "[0-9a-fA-F]{16,64}") String fingerprint,
            @NotNull @Size(min = 1, max = 32)
            Map<@NotBlank @Size(max = 128) String, @NotNull @Size(max = 1000) String> labels,
            @NotNull @Size(max = 32)
            Map<@NotBlank @Size(max = 128) String, @NotNull @Size(max = 2000) String> annotations,
            @NotNull Instant startsAt,
            Instant endsAt) {
        public Alert {
            if (startsAt != null) { startsAt = startsAt.truncatedTo(java.time.temporal.ChronoUnit.MICROS); }
            if (endsAt != null) { endsAt = endsAt.truncatedTo(java.time.temporal.ChronoUnit.MICROS); }
        }

        @AssertTrue(message = "labels.alertname is required")
        public boolean isAlertNamePresent() {
            return labels != null && labels.get("alertname") != null && !labels.get("alertname").isBlank();
        }

        @AssertTrue(message = "resolved alerts require endsAt not earlier than startsAt")
        public boolean isResolutionTimeValid() {
            return status != Status.RESOLVED || (startsAt != null && endsAt != null && !endsAt.isBefore(startsAt));
        }
    }
}
