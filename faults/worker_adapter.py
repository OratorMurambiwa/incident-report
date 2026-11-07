"""Test-only deterministic boundaries around real production worker functions.
No fake DB/Kafka responses, no production fault flags. This entrypoint is only mounted
in private fault-suite containers, never copied into the application image.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import time

import main as worker
from diagnosis import generate_diagnosis
from kafka import KafkaConsumer

CONTROL = Path('/control')
consumer_instance = None
original_settings = worker.Settings.from_env
original_handle = worker.handle_record


def claim_gate(config: dict, event: dict, boundary: str) -> bool:
    if config.get('boundary') != boundary or config.get('event_id') != event['eventId']:
        return False
    marker = CONTROL/(config['case']+'.once')
    try:
        with marker.open('x') as handle:
            handle.write(boundary)
        return True
    except FileExistsError:
        return False


def gate(event: dict, boundary: str) -> None:
    path = CONTROL/'gate.json'
    if not path.exists():
        return
    config = json.loads(path.read_text())
    if not claim_gate(config,event,boundary):
        return
    if config.get('expire_membership'):
        # Pinned kafka-python 2.2.15 private test seam. Disable real heartbeats,
        # retaining the actual member/generation, so the broker expires membership.
        consumer_instance._coordinator._heartbeat_thread.disable()
    (CONTROL/(config['case']+'.ready')).write_text(json.dumps({'boundary':boundary,'event_id':event['eventId']}))
    deadline = time.monotonic()+90
    while not (CONTROL/(config['case']+'.release')).exists():
        if time.monotonic()>deadline:
            raise RuntimeError('Fault gate exceeded its 90-second bound')
        time.sleep(0.05)


def process(event: dict) -> bool:
    gate(event,'before_process')
    def diagnose(payload: dict, documents: list) -> dict:
        gate(payload,'before_commit')  # receipt/snapshots uncommitted in real transaction
        return generate_diagnosis(payload,documents)
    changed = worker.process_event(event,diagnose=diagnose)
    gate(event,'after_commit')  # actual DB context has committed, no offset commit yet
    return changed


def handle(record, consumer, settings, stopped) -> None:
    original_handle(record,consumer,settings,stopped,process=process)


def consumer(*args, **kwargs):
    global consumer_instance
    kwargs.update(session_timeout_ms=6000,heartbeat_interval_ms=1000)
    consumer_instance = KafkaConsumer(*args,**kwargs)
    return consumer_instance


if __name__=='__main__':
    worker.Settings.from_env = classmethod(lambda cls: replace(original_settings(),topic=os.environ['FAULT_TOPIC']))
    worker.KafkaConsumer = consumer
    worker.handle_record = handle
    worker.main()
