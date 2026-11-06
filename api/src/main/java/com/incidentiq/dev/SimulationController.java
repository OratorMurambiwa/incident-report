package com.incidentiq.dev;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/dev/simulate")
@Profile("dev & !prod & !production")
@ConditionalOnProperty(name = "incidentiq.simulation.enabled", havingValue = "true")
public class SimulationController {
    @GetMapping("/failure")
    public ResponseEntity<Map<String, Object>> failure() {
        return ResponseEntity.internalServerError().body(Map.of("simulated", true, "message", "Development-only HTTP 500"));
    }

    @GetMapping("/latency")
    public Map<String, Object> latency(@RequestParam(defaultValue = "750") @Min(0) @Max(2000) int delayMs)
            throws InterruptedException {
        Thread.sleep(delayMs);
        return Map.of("simulated", true, "delayMs", delayMs);
    }
}
