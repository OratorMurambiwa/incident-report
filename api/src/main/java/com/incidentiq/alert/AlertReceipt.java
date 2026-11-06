package com.incidentiq.alert;

import java.util.List;
import java.util.UUID;

public record AlertReceipt(int created, int deduplicated, int resolved, int ignored, List<Action> actions) {
    public enum Outcome { CREATED, DEDUPLICATED, RESOLVED, IGNORED }
    public record Action(String fingerprint, UUID incidentId, Outcome outcome) { }
}
