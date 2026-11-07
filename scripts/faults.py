#!/usr/bin/env python3
"""Real fault injection in a private run-specific Docker project; never targets normal services."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'faults'))
from contracts import names, durable, assert_accounted


def command(args: list[str], env: dict[str,str] | None = None, timeout: int = 180) -> str:
    try:
        return subprocess.check_output(args,cwd=ROOT,env=env,text=True,stderr=subprocess.STDOUT,timeout=timeout)
    except subprocess.CalledProcessError as error:
        print(error.output,file=sys.stderr)
        raise


def wait(check, description: str, timeout: int = 120):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=check()
        if value: return value
        time.sleep(0.3)
    raise AssertionError('Timed out: '+description)


class Suite:
    def __init__(self, run: str):
        self.run=run
        self.ids=names(run)
        self.work=ROOT/'.incidentiq-backups'/'faults'/run
        self.control=self.work/'control'
        self.results=ROOT/'docs'/'faults'/'runs'/run
        self.control.mkdir(parents=True)
        self.results.mkdir(parents=True)
        self.env=dict(os.environ,FAULT_RUN=run,FAULT_DB=self.ids['database'],FAULT_TOPIC=self.ids['topic'],
                      FAULT_CONTROL=str(self.control),FAULT_PASSWORD=uuid.uuid4().hex)
        self.base=['docker','compose','-p',self.ids['project'],'--project-directory',str(ROOT),'-f','faults/compose.yaml']
        self.expected=[]
        self.report={'run':run,**self.ids,'mode':'RETRIEVAL_ONLY','exactly_once_delivery_claimed':False,'cases':[]}
        self.children=[]

    def dc(self,*args: str,timeout: int = 180) -> str:
        return command(self.base+list(args),self.env,timeout)

    def ctl(self,action: str,*args: str) -> dict:
        return json.loads(self.dc('exec','-T','fault-driver','python','/faults/control.py',action,*args,timeout=40))

    def state(self,service: str='fault-worker') -> dict:
        cid=self.dc('ps','-aq',service).strip()
        if not cid: return {'restarts':0,'running':False,'paused':False,'oom':False,'absent':True}
        return json.loads(command(['docker','inspect','--format',
            '{"restarts":{{.RestartCount}},"running":{{.State.Running}},"paused":{{.State.Paused}},"oom":{{.State.OOMKilled}}}',cid]))

    def snapshot(self) -> dict:
        return self.ctl('snapshot')

    def row(self,event: dict) -> dict:
        return next(row for row in self.snapshot()['rows'] if row['event_id']==event['event_id'])

    def create(self,case: str) -> dict:
        payload={'service':'fault-'+case+'-'+self.run,'title':'Synthetic '+case,
                 'description':'PostgreSQL too many clients, connection pool exhausted, SQLSTATE 08006.','severity':'HIGH'}
        request=urllib.request.Request('http://127.0.0.1:18081/api/incidents',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=10) as response:
            assert response.status==201
            incident=json.load(response)
        row=next(r for r in self.snapshot()['rows'] if r['incident_id']==incident['id'])
        self.expected.append(row['event_id'])
        return row

    def settled(self,event: dict,timeout: int=120) -> dict:
        def check():
            row=self.row(event)
            if not durable(row): return None
            offsets=self.ctl('kafka')
            return {'row':row,'offsets':offsets} if offsets['committed']==offsets['end'] else None
        return wait(check,'durable outcome and offset for '+event['event_id'],timeout)

    def record(self,name: str,start: float,**fields) -> None:
        value={'case':name,'recovery_seconds':round(time.monotonic()-start,3),**fields}
        self.report['cases'].append(value)
        print('PASS',name,json.dumps(value),flush=True)
        self.save()

    def save(self) -> None:
        (self.results/'results.json').write_text(json.dumps(self.report,indent=2)+'\n')

    def gate(self,event: dict,case: str,boundary: str,expire: bool=False) -> None:
        path=self.control/'gate.tmp'
        path.write_text(json.dumps({'case':case,'event_id':event['event_id'],'boundary':boundary,'expire_membership':expire}))
        path.replace(self.control/'gate.json')

    def release(self,case: str) -> None:
        (self.control/(case+'.release')).write_text('release')

    def gated_event(self,case: str,boundary: str,expire: bool=False) -> dict:
        self.dc('pause','fault-publisher')
        try:
            event=self.create(case)
            self.gate(event,case,boundary,expire)
        finally:
            self.dc('unpause','fault-publisher')
        wait(lambda:(self.control/(case+'.ready')).exists(),case+' gate',90)
        return event

    def crash(self,case: str,boundary: str) -> None:
        event=self.gated_event(case,boundary)
        before=self.row(event)
        offsets=self.ctl('kafka')
        assert offsets['committed']<offsets['end']
        if boundary=='before_commit':
            assert before['receipts']==before['diagnoses']==before['snapshots']==0
        else:
            assert before['receipts']==before['diagnoses']==1 and before['snapshots']==5
        start=time.monotonic()
        self.dc('kill','-s','KILL','fault-worker')
        self.release(case)
        self.dc('up','-d','--no-deps','--wait','fault-worker')
        after=self.settled(event)
        if boundary=='after_commit':
            assert before['diagnosis_id']==after['row']['diagnosis_id']
            assert before['snapshot_hash']==after['row']['snapshot_hash']
        self.record(case,start,before=before,after=after,worker_state=self.state())

    def rebalance(self) -> None:
        event=self.create('duplicates')
        before=self.settled(event)['row']
        # Free API/publisher memory before bringing up a second real model worker.
        self.dc('stop','fault-api','fault-publisher')
        start=time.monotonic()
        self.dc('up','-d','--wait','fault-peer')
        two=wait(lambda:(s if (s:=self.ctl('kafka'))['members']==2 and s['group_state']=='Stable' else None),'two group members')
        duplicate=self.ctl('duplicate',event['event_id'],'--copies','3')
        after=self.settled(event)
        assert before['diagnosis_id']==after['row']['diagnosis_id'] and before['snapshot_hash']==after['row']['snapshot_hash']
        self.dc('stop','fault-peer')
        one=wait(lambda:(s if (s:=self.ctl('kafka'))['members']==1 and s['group_state']=='Stable' else None),'one member after rebalance')
        self.record('duplicates_and_rebalance',start,duplicates=duplicate,two_members=two,after=after,one_member=one)
        self.dc('up','-d','--wait','fault-api','fault-publisher')

    def broker_outage(self) -> None:
        self.dc('stop','fault-kafka')
        events=[self.create('broker_outage') for _ in range(3)]
        wait(lambda:any(self.row(e)['outbox_attempts']>0 for e in events),'persisted outbox retry during broker outage',40)
        before=self.snapshot()
        assert all(self.row(e)['diagnoses']==0 for e in events)
        start=time.monotonic()
        self.dc('up','-d','--wait','fault-kafka')
        after=[self.settled(e) for e in events]
        self.record('broker_outage',start,recovered_events=after,outbox_retry_observed=True,quarantine_before=len(before['quarantined']))

    def database_outage(self) -> None:
        event=self.gated_event('database_outage','before_process')
        before=self.ctl('kafka')
        baseline=self.state()['restarts']
        self.dc('stop','fault-postgres')
        self.release('database_outage')
        wait(lambda:self.state()['restarts']>baseline,'worker fails closed when quarantine cannot persist',40)
        during=self.ctl('kafka')
        assert during['committed']==before['committed']<during['end']
        start=time.monotonic()
        self.dc('up','-d','--wait','fault-postgres')
        after=self.settled(event)
        self.record('database_outage',start,before=before,during=during,after=after,worker_state=self.state())

    def publisher_crash(self) -> None:
        self.dc('pause','fault-publisher')
        event=self.create('publisher_crash')
        log=(self.work/'publisher-gate.log').open('w')
        holder=subprocess.Popen(self.base+['exec','-T','fault-driver','python','/faults/control.py','hold',event['event_id']],cwd=ROOT,env=self.env,stdout=log,stderr=subprocess.STDOUT)
        self.children.append((holder,log))
        wait(lambda:(self.control/'publisher.ready').exists(),'publisher advisory lock ready',20)
        self.dc('unpause','fault-publisher')
        def acked():
            row=self.row(event)
            return row if row['diagnoses']==1 and not row['published'] and self.snapshot()['publisher_gate_waiters']>=1 else None
        before=wait(acked,'Kafka ack and diagnosis before outbox update commit',60)
        start=time.monotonic()
        self.dc('kill','-s','KILL','fault-publisher')
        (self.control/'publisher.release').write_text('release')
        assert holder.wait(timeout=10)==0
        self.dc('up','-d','fault-publisher')
        after=self.settled(event)
        assert before['diagnosis_id']==after['row']['diagnosis_id'] and before['snapshot_hash']==after['row']['snapshot_hash']
        copies=self.ctl('records')['event_copies'][event['event_id']]
        assert copies>=2
        self.record('publisher_crash_after_kafka_ack',start,before=before,after=after,kafka_copies=copies,publisher_state=self.state('fault-publisher'))

    def member_expiry(self) -> None:
        baseline=self.state()['restarts']
        event=self.gated_event('member_expiry','after_commit',expire=True)
        before=self.row(event)
        offset_before=self.ctl('kafka')
        assert before['diagnoses']==1 and offset_before['committed']<offset_before['end']
        expired=wait(lambda:(s if (s:=self.ctl('kafka'))['members']==0 else None),'real broker expires stale member',25)
        start=time.monotonic()
        self.release('member_expiry')
        wait(lambda:self.state()['restarts']>baseline,'stale commit aborts worker',40)
        after=self.settled(event)
        logs=self.dc('logs','--no-color','fault-worker')
        current=logs[logs.index('"eventId": "'+event['event_id']+'"'):]
        assert 'UnknownMemberIdError' in current and 'CommitFailedError' in current
        assert before['diagnosis_id']==after['row']['diagnosis_id'] and before['snapshot_hash']==after['row']['snapshot_hash']
        self.record('unknown_member_id_recovery',start,before=before,expired_group=expired,after=after,worker_state=self.state(),broker_error='UnknownMemberIdError',client_error='CommitFailedError')

    def poison(self) -> dict:
        start=time.monotonic()
        sent=self.ctl('poison')
        def retained():
            rows=self.snapshot()['quarantined']
            offsets=self.ctl('kafka')
            return {'rows':rows,'offsets':offsets} if len(rows)==1 and offsets['committed']==offsets['end'] else None
        after=wait(retained,'durable poison and offset')
        assert after['rows'][0]['payload_sha256']==sent['payload_sha256']
        self.record('poison_retained',start,after=after)
        return after['rows'][0]

    def run_suite(self) -> None:
        self.dc('config','--quiet')
        self.dc('up','-d','--wait','fault-postgres','fault-kafka','fault-api','fault-driver')
        self.dc('exec','-T','fault-kafka','/opt/kafka/bin/kafka-topics.sh','--bootstrap-server','fault-kafka:9092','--create','--topic',self.ids['topic'],'--partitions','1','--replication-factor','1')
        self.ctl('init')
        self.dc('run','--rm','-T','--no-deps','fault-worker','python','ingest.py','/runbooks')
        self.dc('up','-d','--wait','fault-worker','fault-publisher')
        warm=self.create('warmup');self.settled(warm)
        self.crash('crash_before_db_commit','before_commit')
        self.crash('crash_after_db_commit','after_commit')
        self.rebalance()
        self.broker_outage()
        self.database_outage()
        self.publisher_crash()
        self.member_expiry()
        poison=self.poison()
        final=self.snapshot();offsets=self.ctl('kafka');records=self.ctl('records')
        assert len(final['rows'])==len(self.expected)==10
        assert len(final['quarantined'])==1
        assert_accounted(final['rows'],records,offsets,poison)
        logs=self.dc('logs','--no-color','fault-worker','fault-peer')
        duplicate_logs=[json.loads(line[line.index('{'):]) for line in logs.splitlines() if '{"action": "duplicate"' in line]
        assert len(duplicate_logs)>=6
        self.report.update(complete=True,valid_events=len(self.expected),committed_diagnoses=sum(r['diagnoses'] for r in final['rows']),
                           data_loss=0,quarantined=final['quarantined'],raw_kafka=records,offsets=offsets,
                           duplicate_handlings=len(duplicate_logs),final_rows=final['rows'])
        self.save()

    def teardown(self) -> None:
        for case in ('crash_before_db_commit','crash_after_db_commit','database_outage','member_expiry','publisher'):
            self.release(case)
        for service in ('fault-worker','fault-peer','fault-publisher','fault-postgres','fault-kafka'):
            try:
                if self.state(service)['paused']: self.dc('unpause',service)
            except subprocess.CalledProcessError:
                pass
        self.dc('stop','--timeout','10')  # containers AND all volumes retained for review
        for child,log in self.children:
            if child.poll() is None: child.terminate()
            log.close()
        for service in ('fault-worker','fault-peer','fault-publisher','fault-kafka','fault-postgres','fault-api'):
            (self.work/(service+'.log')).write_text(self.dc('logs','--no-color',service))


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run',))
    parser.parse_args()
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if available<3_000_000_000: raise RuntimeError('Need at least 3 GB available RAM')
    run=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'_'+uuid.uuid4().hex[:8]
    lock=ROOT/'.incidentiq-backups'/'faults'/'active.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as handle: handle.write(run)
    suite=None
    try:
        suite=Suite(run)
        files=sorted((ROOT/'faults').glob('*.py'))+[ROOT/'faults'/'compose.yaml',Path(__file__).resolve()]
        conditions={'run':run,**suite.ids,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'timezone':'America/Chicago',
                    'application_commit':command(['git','rev-parse','HEAD']).strip(),'memory_available_before':available,
                    'cpu_model':next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),
                    'logical_cpus':os.cpu_count(),'session_timeout_ms':6000,'heartbeat_interval_ms':1000,
                    'normal_worker_timeouts_unchanged':True,'mode':'RETRIEVAL_ONLY',
                    'images':{image:json.loads(command(['docker','image','inspect',image,'--format','{{json .Id}}'])) for image in ('incidentiq-api:local','incidentiq-worker:local','apache/kafka:3.9.1','pgvector/pgvector:0.8.7-pg16-trixie')},
                    'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        (suite.results/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
        print('Private fault run:',run,'project:',suite.ids['project'],flush=True)
        suite.run_suite()
        print(json.dumps(suite.report,indent=2),flush=True)
    finally:
        if suite:
            try: suite.teardown()
            finally:
                suite.report.setdefault('complete',False)
                suite.save()
                print('Stopped only private test containers; all test/normal volumes retained.',flush=True)
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    main()
