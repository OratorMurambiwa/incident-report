"""Private-suite DB/Kafka observer and injector. Run only inside fault-driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from db import connect_db
from kafka import KafkaConsumer,KafkaProducer,TopicPartition
from kafka.admin import KafkaAdminClient

TOPIC=os.environ['FAULT_TOPIC']
GROUP=os.environ['KAFKA_GROUP_ID']
BOOTSTRAP=os.environ['KAFKA_BOOTSTRAP_SERVERS']


def snapshot() -> dict:
    with connect_db() as connection, connection.cursor() as cursor:
        cursor.execute('''SELECT i.id,o.event_id,i.status,o.published_at IS NOT NULL,o.attempts,
                         (SELECT count(*) FROM incidentiq_api.processed_events p WHERE p.incident_id=i.id),
                         (SELECT count(*) FROM incidentiq_api.diagnoses d WHERE d.incident_id=i.id),
                         (SELECT count(*) FROM incidentiq_api.incident_retrievals r WHERE r.incident_id=i.id),
                         (SELECT md5(string_agg(row(r.rank,r.chunk_id,r.content,r.source,r.similarity,r.retrieved_at)::text,'' ORDER BY rank))
                           FROM incidentiq_api.incident_retrievals r WHERE r.incident_id=i.id),
                         (SELECT d.id FROM incidentiq_api.diagnoses d WHERE d.incident_id=i.id)
                         FROM incidentiq_api.incidents i JOIN incidentiq_api.outbox_events o ON o.incident_id=i.id ORDER BY i.created_at,i.id''')
        rows=[dict(zip(('incident_id','event_id','status','published','outbox_attempts','receipts','diagnoses','snapshots','snapshot_hash','diagnosis_id'),row)) for row in cursor.fetchall()]
        cursor.execute("SELECT offset_id,error_code,attempts,encode(payload,'hex') FROM incidentiq_api.failed_events ORDER BY offset_id")
        failures=[{'offset':r[0],'error':r[1],'attempts':r[2],'payload_sha256':hashlib.sha256(bytes.fromhex(r[3])).hexdigest()} for r in cursor.fetchall()]
        cursor.execute("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND objid=4773 AND NOT granted")
        waiting=cursor.fetchone()[0]
    return {'rows':rows,'quarantined':failures,'publisher_gate_waiters':waiting}


def kafka_state() -> dict:
    client=KafkaConsumer(bootstrap_servers=BOOTSTRAP,group_id=GROUP,enable_auto_commit=False,request_timeout_ms=15000)
    tp=TopicPartition(TOPIC,0)
    result={'end':client.end_offsets([tp])[tp],'committed':client.committed(tp)}
    client.close(autocommit=False)
    admin=KafkaAdminClient(bootstrap_servers=BOOTSTRAP,request_timeout_ms=15000)
    info=admin.describe_consumer_groups([GROUP])[0]
    result.update(group_state=info.state,members=len(info.members))
    admin.close()
    return result


def initialize() -> dict:
    with connect_db() as connection, connection.cursor() as cursor:
        # Run-specific routing is part of the isolated fixture schema only. This
        # avoids changing API defaults or ever publishing on the normal topic.
        cursor.execute('CREATE SCHEMA fault_harness')
        cursor.execute('CREATE TABLE fault_harness.publisher_gate (event_id uuid PRIMARY KEY)')
        cursor.execute("SELECT set_config('fault.topic',%s,true)",(TOPIC,))
        cursor.execute('''CREATE FUNCTION fault_harness.route() RETURNS trigger LANGUAGE plpgsql AS $$
                          BEGIN NEW.topic := TG_ARGV[0]; RETURN NEW; END $$''')
        from psycopg import sql
        cursor.execute('ALTER TABLE incidentiq_api.outbox_events DROP CONSTRAINT outbox_events_topic_check')
        cursor.execute(sql.SQL('ALTER TABLE incidentiq_api.outbox_events ADD CONSTRAINT outbox_events_topic_check CHECK (topic={})').format(sql.Literal(TOPIC)))
        cursor.execute(sql.SQL('CREATE TRIGGER fault_route BEFORE INSERT ON incidentiq_api.outbox_events FOR EACH ROW EXECUTE FUNCTION fault_harness.route({})').format(sql.Literal(TOPIC)))
        cursor.execute('''CREATE FUNCTION fault_harness.block_publication() RETURNS trigger LANGUAGE plpgsql AS $$
                          BEGIN
                            IF EXISTS(SELECT 1 FROM fault_harness.publisher_gate WHERE event_id=NEW.event_id) THEN
                              PERFORM pg_advisory_xact_lock(4773);
                            END IF;
                            RETURN NEW;
                          END $$''')
        cursor.execute('''CREATE TRIGGER fault_publication BEFORE UPDATE OF published_at ON incidentiq_api.outbox_events
                          FOR EACH ROW WHEN (NEW.published_at IS NOT NULL) EXECUTE FUNCTION fault_harness.block_publication()''')
    return {'initialized':True}


def duplicate(event_id: str, copies: int) -> dict:
    with connect_db() as connection:
        payload=connection.execute('SELECT payload::text FROM incidentiq_api.outbox_events WHERE event_id=%s',(event_id,)).fetchone()[0]
    producer=KafkaProducer(bootstrap_servers=BOOTSTRAP,acks='all',retries=3)
    offsets=[]
    for _ in range(copies):
        offsets.append(producer.send(TOPIC,value=payload.encode()).get(timeout=15).offset)
    producer.close(timeout=5)
    return {'duplicate_offsets':offsets}


def records() -> dict:
    consumer=KafkaConsumer(bootstrap_servers=BOOTSTRAP,group_id=None,enable_auto_commit=False,
                           request_timeout_ms=10000,api_version_auto_timeout_ms=5000)
    tp=TopicPartition(TOPIC,0)
    consumer.assign([tp]);consumer.seek(tp,0)  # fresh test topic: avoid lazy reset lookup in position()
    end=consumer.end_offsets([tp])[tp]
    counts={};invalid=0;deadline=time.monotonic()+30
    while consumer.position(tp)<end and time.monotonic()<deadline:
        for batch in consumer.poll(timeout_ms=200).values():
            for message in batch:
                try:
                    event_id=json.loads(message.value)['eventId']
                except (ValueError,KeyError,TypeError):
                    invalid+=1;continue
                counts[event_id]=counts.get(event_id,0)+1
    assert consumer.position(tp)>=end
    consumer.close(autocommit=False)
    return {'event_copies':counts,'invalid_records':invalid,'end':end}


def hold_publisher(event_id: str) -> None:
    with connect_db() as connection:
        connection.execute('INSERT INTO fault_harness.publisher_gate VALUES (%s)',(event_id,))
    with connect_db() as connection:
        connection.execute('SELECT pg_advisory_lock(4773)')
        Path('/control/publisher.ready').write_text(event_id)
        deadline=time.monotonic()+90
        while not Path('/control/publisher.release').exists():
            if time.monotonic()>deadline: raise RuntimeError('Publisher gate timed out')
            time.sleep(0.05)
        connection.execute('SELECT pg_advisory_unlock(4773)')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('snapshot','kafka','init','duplicate','records','hold','poison'))
    parser.add_argument('event_id',nargs='?')
    parser.add_argument('--copies',type=int,default=3)
    args=parser.parse_args()
    if args.action=='hold':
        hold_publisher(args.event_id)
    elif args.action=='duplicate':
        print(json.dumps(duplicate(args.event_id,args.copies)))
    elif args.action=='poison':
        producer=KafkaProducer(bootstrap_servers=BOOTSTRAP,acks='all')
        payload=b'{invalid-fault-test-json}'
        offset=producer.send(TOPIC,value=payload).get(timeout=15).offset
        producer.close(timeout=5)
        print(json.dumps({'offset':offset,'payload_sha256':hashlib.sha256(payload).hexdigest()}))
    else:
        result={'snapshot':snapshot,'kafka':kafka_state,'init':initialize,'records':records}[args.action]()
        print(json.dumps(result,default=str))
