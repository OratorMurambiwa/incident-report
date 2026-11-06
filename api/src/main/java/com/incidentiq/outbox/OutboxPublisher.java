package com.incidentiq.outbox;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "outbox.publisher.enabled", havingValue = "true")
public class OutboxPublisher {
    private final OutboxDelivery delivery;

    public OutboxPublisher(OutboxDelivery delivery) { this.delivery = delivery; }

    @Scheduled(fixedDelayString = "${outbox.publisher.delay-ms:1000}")
    public void publish() {
        for (int i = 0; i < 20 && !Thread.currentThread().isInterrupted(); i++) {
            if (!delivery.publishNext()) { break; }
        }
    }
}
