"""Pure validation/accounting used by the private fault suite."""
import re

RUN = re.compile(r'[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}')


def names(run: str) -> dict[str, str]:
    if not RUN.fullmatch(run):
        raise ValueError('Invalid fault run identifier')
    return {'project':'incidentiq-fault-'+run,'database':'incidentiq_fault_'+run,
            'topic':'incidentiq.fault.'+run}


def durable(row: dict) -> bool:
    return (row['published'] and row['status']=='RECEIVED' and row['receipts']==1
            and row['diagnoses']==1 and row['snapshots']==5)


def assert_accounted(rows: list[dict], records: dict, offsets: dict, poison: dict) -> None:
    if not rows or not all(durable(row) for row in rows):
        raise AssertionError('Missing/duplicate durable incident effects')
    ids = {row['event_id'] for row in rows}
    if ids != records['event_copies'].keys():
        raise AssertionError('Kafka/DB event IDs are not fully accounted')
    if any(value<1 for value in records['event_copies'].values()):
        raise AssertionError('Missing Kafka record')
    if records['invalid_records']!=1 or poison['error']!='InvalidEvent' or poison['attempts']!=1:
        raise AssertionError('Poison record not durably retained')
    if offsets['committed']!=offsets['end'] or offsets['end']!=records['end']:
        raise AssertionError('Consumer offsets do not cover durable outcomes')
