package com.incidentiq;

import com.incidentiq.outbox.*;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OutboxDeliveryTest {
    @Mock OutboxStore store;
    @Mock KafkaTemplate<String, String> kafka;
    private final OutboxStore.PendingEvent event = new OutboxStore.PendingEvent(
            UUID.randomUUID(), UUID.randomUUID(), "incident.created", "{\"schemaVersion\":1}", 0);

    @Test
    void publishesWithIncidentKeyAndMarksOnlyAfterAcknowledgement() {
        when(store.lockNext()).thenReturn(Optional.of(event));
        when(kafka.send(event.topic(), event.incidentId().toString(), event.payload()))
                .thenReturn(CompletableFuture.completedFuture(null));
        assertTrue(new OutboxDelivery(store, kafka).publishNext());
        var order = inOrder(kafka, store);
        order.verify(kafka).send(event.topic(), event.incidentId().toString(), event.payload());
        order.verify(store).published(event.eventId());
        verify(store, never()).retry(any(), anyString());
    }

    @Test
    void sendFailureSchedulesRetryAndLaterSuccessMarksPublished() {
        when(store.lockNext()).thenReturn(Optional.of(event));
        when(kafka.send(anyString(), anyString(), anyString()))
                .thenReturn(CompletableFuture.failedFuture(new RuntimeException("unavailable")))
                .thenReturn(CompletableFuture.completedFuture(null));
        var delivery = new OutboxDelivery(store, kafka);
        assertTrue(delivery.publishNext());
        verify(store).retry(event, "ExecutionException");
        verify(store, never()).published(any());
        assertTrue(delivery.publishNext());
        verify(store).published(event.eventId());
    }

    @Test
    void databaseFailureAfterAckPropagatesForRollbackAndReplay() {
        when(store.lockNext()).thenReturn(Optional.of(event));
        when(kafka.send(anyString(), anyString(), anyString())).thenReturn(CompletableFuture.completedFuture(null));
        doThrow(new IllegalStateException("database unavailable")).when(store).published(event.eventId());
        assertThrows(IllegalStateException.class, () -> new OutboxDelivery(store, kafka).publishNext());
        verify(store, never()).retry(any(), anyString());
    }

    @Test
    void emptyOutboxDoesNotContactKafka() {
        when(store.lockNext()).thenReturn(Optional.empty());
        assertFalse(new OutboxDelivery(store, kafka).publishNext());
        verifyNoInteractions(kafka);
    }
}
