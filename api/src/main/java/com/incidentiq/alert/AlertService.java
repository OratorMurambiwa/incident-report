package com.incidentiq.alert;

import com.incidentiq.incident.CreateIncidentRequest;
import com.incidentiq.incident.IncidentService;
import com.incidentiq.incident.Severity;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Locale;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static com.incidentiq.alert.AlertReceipt.Outcome.*;

@Service
public class AlertService {
    private final AlertRepository alerts;
    private final IncidentService incidents;

    public AlertService(AlertRepository alerts, IncidentService incidents) {
        this.alerts = alerts;
        this.incidents = incidents;
    }

    @Transactional
    public AlertReceipt accept(AlertmanagerNotification notification) {
        var actions = new ArrayList<AlertReceipt.Action>();
        // Stable lock order prevents opposite-order batches from deadlocking.
        var ordered = notification.alerts().stream()
                .sorted(Comparator.comparing(a -> a.fingerprint().toLowerCase(Locale.ROOT))).toList();
        for (var alert : ordered) {
            String fingerprint = alert.fingerprint().toLowerCase(Locale.ROOT);
            var state = alerts.lock(fingerprint);
            if (alert.status() == AlertmanagerNotification.Status.FIRING) {
                if (state.resolvedThrough() != null && !alert.startsAt().isAfter(state.resolvedThrough())) {
                    actions.add(new AlertReceipt.Action(fingerprint, null, IGNORED));
                } else if (state.incidentId() != null) {
                    if (alert.startsAt().isAfter(state.startsAt())) { alerts.advanceStart(fingerprint, alert.startsAt()); }
                    actions.add(new AlertReceipt.Action(fingerprint, state.incidentId(), DEDUPLICATED));
                } else {
                    String service = bounded(alert.labels().getOrDefault("service", alert.labels().getOrDefault("job", "monitoring")), 100);
                    String title = bounded("Alert: " + alert.labels().get("alertname") + " — "
                            + alert.annotations().getOrDefault("summary", "Monitoring threshold exceeded"), 200);
                    String description = bounded("Untrusted Alertmanager evidence; investigate before remediation.\n"
                            + "Fingerprint: " + fingerprint + "\nStarts at: " + alert.startsAt()
                            + "\nLabels: " + alert.labels() + "\nAnnotations: " + alert.annotations(), 10000);
                    var created = incidents.create(new CreateIncidentRequest(service.isBlank() ? "monitoring" : service,
                            title, description, severity(alert.labels().get("severity"))));
                    alerts.activate(fingerprint, created.id(), alert);
                    actions.add(new AlertReceipt.Action(fingerprint, created.id(), CREATED));
                }
            } else if (state.incidentId() != null && alert.startsAt().isBefore(state.startsAt())) {
                actions.add(new AlertReceipt.Action(fingerprint, state.incidentId(), IGNORED));
            } else {
                alerts.resolve(fingerprint, state.incidentId(), alert.endsAt());
                actions.add(new AlertReceipt.Action(fingerprint, state.incidentId(), state.incidentId() == null ? IGNORED : RESOLVED));
            }
        }
        return new AlertReceipt(count(actions, CREATED), count(actions, DEDUPLICATED), count(actions, RESOLVED), count(actions, IGNORED), actions);
    }

    private static int count(java.util.List<AlertReceipt.Action> actions, AlertReceipt.Outcome outcome) {
        return (int) actions.stream().filter(action -> action.outcome() == outcome).count();
    }

    private static Severity severity(String severity) {
        if (severity == null) { return Severity.HIGH; }
        return switch (severity.toLowerCase(Locale.ROOT)) {
            case "critical" -> Severity.CRITICAL;
            case "warning" -> Severity.MEDIUM;
            case "info" -> Severity.LOW;
            default -> Severity.HIGH;
        };
    }

    private static String bounded(String value, int max) { return value.strip().substring(0, Math.min(value.strip().length(), max)); }
}
