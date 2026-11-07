"""Observe actual Kafka LogAppendTime to committed diagnosis visibility. No app offsets committed."""
import json
import os
from pathlib import Path
import time

from kafka import KafkaConsumer, TopicPartition
from db import connect_db
from measurements import summarize


def main() -> None:
    run = os.environ['BENCH_RUN']
    service = 'bench-async-' + run
    with connect_db() as connection, connection.cursor() as cursor:
        cursor.execute('''SELECT o.event_id FROM incidentiq_api.outbox_events o
                          JOIN incidentiq_api.incidents i ON i.id=o.incident_id WHERE i.service=%s''', (service,))
        expected = {str(row[0]) for row in cursor.fetchall()}
    if len(expected) != 60:
        raise RuntimeError('Exactly 60 isolated asynchronous inputs required')
    consumer = KafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                             enable_auto_commit=False, group_id=None)
    partition = TopicPartition('incident.created', 0)
    consumer.assign([partition])
    consumer.seek_to_beginning(partition)
    Path('/work/observer-ready').write_text('ready')
    appended: dict[str, float] = {}
    visible: dict[str, float] = {}
    duplicates = 0
    max_cycle = 0.0
    previous = time.monotonic()
    deadline = previous + 120
    connection = connect_db()
    connection.autocommit = True  # every query sees a fresh committed snapshot
    with connection, connection.cursor() as cursor:
        while time.monotonic() < deadline:
            for records in consumer.poll(timeout_ms=100, max_records=200).values():
                for record in records:
                    event_id = json.loads(record.value)['eventId']
                    if event_id not in expected:
                        continue
                    if record.timestamp_type != 1:
                        raise RuntimeError('Broker must use LogAppendTime for comparable timestamps')
                    if event_id in appended:
                        duplicates += 1
                    appended.setdefault(event_id, record.timestamp / 1000)
            cursor.execute('''SELECT o.event_id, extract(epoch FROM clock_timestamp())::float8
                              FROM incidentiq_api.outbox_events o
                              JOIN incidentiq_api.incidents i ON i.id=o.incident_id
                              JOIN incidentiq_api.diagnoses d ON d.incident_id=i.id
                              WHERE i.service=%s AND d.mode='RETRIEVAL_ONLY' ''', (service,))
            for event_id, observed in cursor.fetchall():
                visible.setdefault(str(event_id), observed)
            now = time.monotonic()
            max_cycle = max(max_cycle, now - previous)
            previous = now
            if len(visible) == len(appended) == len(expected):
                break
        cursor.execute('''SELECT count(*), count(*) FILTER (WHERE i.status='RECEIVED'),
                          (SELECT count(*) FROM incidentiq_api.failed_events),
                          (SELECT count(*) FROM incidentiq_api.processed_events p
                            JOIN incidentiq_api.incidents x ON x.id=p.incident_id WHERE x.service=%s),
                          (SELECT count(*) FROM incidentiq_api.incident_retrievals r
                            JOIN incidentiq_api.incidents x ON x.id=r.incident_id WHERE x.service=%s),
                          count(*) FILTER (WHERE o.published_at IS NOT NULL)
                          FROM incidentiq_api.incidents i JOIN incidentiq_api.outbox_events o ON o.incident_id=i.id
                          WHERE i.service=%s''', (service, service, service))
        count, received, failures, receipts, snapshots, published = cursor.fetchone()
    consumer.close(autocommit=False)
    group = KafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'], group_id=run, enable_auto_commit=False)
    end_offset = group.end_offsets([partition])[partition]
    committed = group.committed(partition)
    for _ in range(30):
        if committed is not None and committed >= end_offset:
            break
        time.sleep(0.1)
        committed = group.committed(partition)
    group.close(autocommit=False)
    complete = expected == appended.keys() == visible.keys()
    result = {'mode':'RETRIEVAL_ONLY', 'expected':len(expected), 'kafka_events':len(appended),
              'committed_diagnoses':len(visible), 'received':received, 'failures':failures,
              'receipts':receipts, 'snapshots':snapshots, 'published_outbox':published,
              'duplicates':duplicates, 'consumer_end_offset':end_offset, 'consumer_committed_offset':committed,
              'max_observer_cycle_ms':max_cycle*1000, 'complete':complete}
    if complete:
        samples = [(visible[event_id]-appended[event_id])*1000 for event_id in sorted(expected)]
        result['latency'] = summarize(samples)
        result['window_seconds'] = max(visible.values())-min(appended.values())
        result['events_per_second'] = len(expected)/result['window_seconds']
        result['error_rate'] = failures/len(expected)
        result['samples_ms'] = samples
    Path('/results/async.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    assert complete and count == received == receipts == published == 60
    assert snapshots == 300 and failures == 0
    assert committed is not None and committed >= end_offset


if __name__ == '__main__':
    main()
