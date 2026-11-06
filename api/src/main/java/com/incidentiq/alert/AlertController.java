package com.incidentiq.alert;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/alerts")
public class AlertController {
    private final AlertService service;
    public AlertController(AlertService service) { this.service = service; }

    @PostMapping("/alertmanager")
    public AlertReceipt accept(@Valid @RequestBody AlertmanagerNotification notification) {
        return service.accept(notification);
    }
}
