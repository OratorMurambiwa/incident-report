package com.incidentiq;

import com.incidentiq.alert.*;
import com.incidentiq.outbox.OutboxStore;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@SpringBootTest
@EnabledIfEnvironmentVariable(named = "RUN_DATABASE_TESTS", matches = "true")
class AlertIntegrationTest {
    @Autowired AlertService service;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager manager;
    @MockitoSpyBean OutboxStore outbox;
    private static final Instant START = Instant.parse("2026-11-05T12:00:00Z");

    private AlertmanagerNotification notification(String fingerprint, boolean resolved, Instant start, Instant end) {
        return new AlertmanagerNotification(AlertmanagerNotification.Status.FIRING, List.of(new AlertmanagerNotification.Alert(
                resolved ? AlertmanagerNotification.Status.RESOLVED : AlertmanagerNotification.Status.FIRING,
                fingerprint, Map.of("alertname", "TestHttp500", "service", "alert-test", "severity", "critical"),
                Map.of("summary", "HTTP 500 server errors"), start, end)));
    }

    private String fingerprint() { return UUID.randomUUID().toString().replace("-", ""); }

    @Test
    void firingCreatesIncidentAndOutboxThenDeduplicates() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            String fp = fingerprint();
            var first = service.accept(notification(fp, false, START, null));
            var duplicate = service.accept(notification(fp.toUpperCase(), false, START, null));
            assertEquals(1, first.created());
            assertEquals(1, duplicate.deduplicated());
            assertEquals(first.actions().getFirst().incidentId(), duplicate.actions().getFirst().incidentId());
            var id = first.actions().getFirst().incidentId();
            assertEquals("CRITICAL", jdbc.queryForObject("SELECT severity FROM incidentiq_api.incidents WHERE id=?", String.class, id));
            assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id=?", Integer.class, id));
            tx.setRollbackOnly();
        });
    }

    @Test
    void resolutionDoesNotPublishAndLateFiringDoesNotReopen() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            String fp = fingerprint();
            var first = service.accept(notification(fp, false, START, null));
            var id = first.actions().getFirst().incidentId();
            assertEquals(1, service.accept(notification(fp, true, START, START.plusSeconds(60))).resolved());
            assertEquals("RESOLVED", jdbc.queryForObject("SELECT status FROM incidentiq_api.incidents WHERE id=?", String.class, id));
            assertEquals(1, service.accept(notification(fp, false, START, null)).ignored());
            assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id=?", Integer.class, id));
            assertEquals(1, service.accept(notification(fp, true, START, START.plusSeconds(60))).ignored());
            tx.setRollbackOnly();
        });
    }

    @Test
    void newEpisodeCreatesNewIncidentAndStaleResolutionCannotCloseIt() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            String fp = fingerprint();
            var old = service.accept(notification(fp, false, START, null));
            service.accept(notification(fp, true, START, START.plusSeconds(30)));
            var fresh = service.accept(notification(fp, false, START.plusSeconds(60), null));
            assertEquals(1, fresh.created());
            assertNotEquals(old.actions().getFirst().incidentId(), fresh.actions().getFirst().incidentId());
            assertEquals(1, service.accept(notification(fp, true, START, START.plusSeconds(30))).ignored());
            assertEquals(fresh.actions().getFirst().incidentId(), jdbc.queryForObject("SELECT active_incident_id FROM incidentiq_api.alert_states WHERE fingerprint=?", UUID.class, fp));
            tx.setRollbackOnly();
        });
    }

    @Test
    void unknownResolutionCreatesOnlyATombstone() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            String fp = fingerprint();
            assertEquals(1, service.accept(notification(fp, true, START, START.plusSeconds(30))).ignored());
            assertEquals(1, service.accept(notification(fp, false, START, null)).ignored());
            assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.alert_incidents WHERE fingerprint=?", Integer.class, fp));
            tx.setRollbackOnly();
        });
    }

    @Test
    void outboxFailureRollsBackFingerprintAndIncident() {
        String fp = fingerprint();
        Long baseline = jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents", Long.class);
        doThrow(new org.springframework.dao.DataAccessResourceFailureException("outbox unavailable")).when(outbox).enqueue(any());
        try {
            assertThrows(org.springframework.dao.DataAccessResourceFailureException.class, () -> service.accept(notification(fp, false, START, null)));
            assertEquals(baseline, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.incidents", Long.class));
            assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM incidentiq_api.alert_states WHERE fingerprint=?", Integer.class, fp));
        } finally { reset(outbox); }
    }

    @Test
    void simultaneousDeliveriesCreateOnlyOneIncident() throws Exception {
        String fp = fingerprint();
        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        try {
            Callable<AlertReceipt> task = () -> { start.await(); return service.accept(notification(fp, false, START, null)); };
            Future<AlertReceipt> a = executor.submit(task);
            Future<AlertReceipt> b = executor.submit(task);
            start.countDown();
            AlertReceipt first = a.get(20, TimeUnit.SECONDS);
            AlertReceipt second = b.get(20, TimeUnit.SECONDS);
            assertEquals(1, first.created() + second.created());
            assertEquals(1, first.deduplicated() + second.deduplicated());
            assertEquals(first.actions().getFirst().incidentId(), second.actions().getFirst().incidentId());
        } finally {
            executor.shutdownNow();
            // Only this isolated test's fixture is removed; application data is never used here.
            UUID id = jdbc.queryForObject("SELECT active_incident_id FROM incidentiq_api.alert_states WHERE fingerprint=?", UUID.class, fp);
            jdbc.update("UPDATE incidentiq_api.alert_states SET active_incident_id=NULL, active_starts_at=NULL WHERE fingerprint=?", fp);
            jdbc.update("DELETE FROM incidentiq_api.alert_incidents WHERE fingerprint=?", fp);
            jdbc.update("DELETE FROM incidentiq_api.alert_states WHERE fingerprint=?", fp);
            jdbc.update("DELETE FROM incidentiq_api.outbox_events WHERE incident_id=?", id);
            jdbc.update("DELETE FROM incidentiq_api.incidents WHERE id=?", id);
        }
    }

    @Test
    void nanosecondNotificationTimesAreCanonicalizedForPostgresReplay() {
        new TransactionTemplate(manager).executeWithoutResult(tx -> {
            String fp = fingerprint();
            var nanos = START.plusNanos(123456789);
            assertEquals(1, service.accept(notification(fp, false, nanos, null)).created());
            assertEquals(1, service.accept(notification(fp, true, nanos, nanos.plusSeconds(60))).resolved());
            tx.setRollbackOnly();
        });
    }
}
