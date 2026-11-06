package com.incidentiq.outbox;

import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OutboxDelivery {
    private static final Logger LOG = LoggerFactory.getLogger(OutboxDelivery.class);
    private final OutboxStore store;
    private final KafkaTemplate<String, String> kafka;

    public OutboxDelivery(OutboxStore store, KafkaTemplate<String, String> kafka) {
        this.store = store;
        this.kafka = kafka;
    }

    @Transactional
    public boolean publishNext() {
        var pending = store.lockNext();
        if (pending.isEmpty()) { return false; }
        var event = pending.get();
        try {
            // Require broker acknowledgement before recording delivery. Crashes can duplicate, never lose, events.
            kafka.send(event.topic(), event.incidentId().toString(), event.payload()).get(15, TimeUnit.SECONDS);
        } catch (Exception exception) {
            if (exception instanceof InterruptedException) { Thread.currentThread().interrupt(); }
            store.retry(event, exception.getClass().getSimpleName());
            LOG.warn("Outbox send failed eventId={} error={}", event.eventId(), exception.getClass().getSimpleName());
            return true;
        }
        // If this database update fails, roll back and resend later (consumer deduplicates eventId).
        store.published(event.eventId());
        LOG.info("Outbox delivered eventId={} incidentId={}", event.eventId(), event.incidentId());
        return true;
    }
}
