#!/usr/bin/env python3
"""Bounded local benchmarks. Only a newly owned database and temporary bench containers are written."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'benchmarks'))
RUN_PATTERN = re.compile(r'[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}')


def database_name(run: str) -> str:
    if not RUN_PATTERN.fullmatch(run):
        raise ValueError('Invalid benchmark run ID')
    return 'incidentiq_bench_' + run


def command(args: list[str], *, env: dict[str, str] | None = None, text: str | None = None,
            timeout: int = 180) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, env=env, input=text, text=True,
                                       stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.CalledProcessError as error:
        print(error.output, file=sys.stderr)
        raise


def admin(sql: str, **variables: str) -> str:
    args = ['docker','compose','exec','-T','postgres','sh','-ec',
            'exec psql -U "$POSTGRES_USER" -d postgres -tA -v ON_ERROR_STOP=1 "$@"','--']
    for key, value in variables.items():
        args += ['-v',key+'='+value]
    return command(args,text=sql).strip()


def cleanup(run: str) -> None:
    name = database_name(run)
    marker = admin("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=:'db';", db=name)
    if marker != 'incidentiq-benchmark:' + run:
        raise RuntimeError('Database ownership marker missing/mismatched; refusing cleanup')
    if admin("SELECT count(*) FROM pg_stat_activity WHERE datname=:'db';",db=name) != '0':
        raise RuntimeError('Benchmark database has active connections; stop its containers first')
    admin("SELECT format('DROP DATABASE %I', :'db') \\gexec\n", db=name)
    print('Removed only owned benchmark database:',name)


def memory() -> dict[str, int]:
    return {line.split(':')[0]: int(line.split()[1])*1024
            for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemTotal','MemAvailable','SwapTotal','SwapFree')}


def wait_http(url: str, timeout: int = 120) -> None:
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=3) as response:
                if response.status==200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError('Benchmark API did not become healthy')


def run_benchmarks() -> None:
    run = datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz')+'_'+uuid.uuid4().hex[:8]
    name = database_name(run)
    work = ROOT/'.incidentiq-backups'/'benchmarks'/run
    results = ROOT/'docs'/'benchmarks'/'runs'/run
    work.mkdir(parents=True)
    results.mkdir(parents=True)
    lock = work.parent/'active.lock'
    # Fixed project/service names require a single benchmark runner. Never overwrite an active lock.
    with lock.open('x') as handle:
        handle.write(run+'\n')
    env = dict(os.environ)
    compose = ['docker','compose','-p','incidentiq-bench','--project-directory',str(ROOT),'-f','benchmarks/compose.yaml']
    created = False
    success = False
    observer = None
    started = time.monotonic()
    try:
        if memory()['MemAvailable'] < 2_900_000_000:
            raise RuntimeError('Need at least 2.9 GB available RAM; no services were changed')
        postgres_id = command(['docker','compose','ps','-q','postgres']).strip()
        network = command(['docker','inspect','--format','{{ index .Config.Labels "com.docker.compose.project" }}',postgres_id]).strip()+'_default'
        for field in ('POSTGRES_USER','POSTGRES_PASSWORD'):
            env[field] = command(['docker','compose','exec','-T','postgres','printenv',field]).strip()
        env.update(BENCH_RUN=run, BENCH_DB=name, BENCH_NETWORK=network,
                   BENCH_WORK=str(work), BENCH_RESULTS=str(results))
        def dc(*args: str, timeout: int = 180, text: str | None = None) -> str:
            return command(compose+list(args),env=env,timeout=timeout,text=text)
        dc('config','--quiet')  # never serialize resolved Compose environment/passwords
        versions = {}
        for image in ('incidentiq-api:local','incidentiq-worker:local','apache/kafka:3.9.1','grafana/k6:1.3.0'):
            versions[image] = json.loads(command(['docker','image','inspect',image,'--format','{{json .Id}}']))
        sources = sorted((ROOT/'benchmarks').glob('*.py')) + [ROOT/'benchmarks'/'api.js',ROOT/'benchmarks'/'compose.yaml',Path(__file__).resolve()]
        conditions = {'run':run,'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'timezone':'America/Chicago',
                      'database':name,'mode':'RETRIEVAL_ONLY','ollama_tested':False,
                      'cpu_model':next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
                      'logical_cpus':os.cpu_count(),'memory_before':memory(),'images':versions,
                      'application_commit':command(['git','rev-parse','HEAD']).strip(),
                      'harness_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                      'bounds':{'read_vus':4,'read_seconds':20,'warmup_vus':2,'warmup_seconds':5,
                                'write_vus':2,'write_iterations':40,'write_max_seconds':20,
                                'async_events':60,'async_timeout_seconds':120,'observer_poll_ms':100},
                      'environment':'Existing local platform running; shared PostgreSQL server, isolated DB and separate Kafka broker. No benchmark Prometheus scrape.'}
        (results/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
        admin("SELECT format('CREATE DATABASE %I', :'db') \\gexec\n"
              "SELECT format('COMMENT ON DATABASE %I IS %L', :'db', :'marker') \\gexec\n",
              db=name, marker='incidentiq-benchmark:'+run)
        created = True
        print('Run:',run,'isolated database:',name,flush=True)
        dc('up','-d','--wait','bench-api','bench-kafka')
        wait_http('http://127.0.0.1:18080/actuator/health')
        dc('exec','-T','bench-kafka','/opt/kafka/bin/kafka-topics.sh','--bootstrap-server','bench-kafka:9092',
           '--create','--topic','incident.created','--partitions','1','--replication-factor','1')
        ids = []
        for i in range(24):
            payload = {'service':'bench-seed-'+run,'title':'Synthetic database incident '+str(i),
                       'description':'PostgreSQL connection pool exhausted, too many clients.','severity':'HIGH'}
            request = urllib.request.Request('http://127.0.0.1:18080/api/incidents', data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=5) as response:
                assert response.status==201
                ids.append(json.load(response)['id'])
        (work/'fixtures.json').write_text(json.dumps({'ids':ids}))
        for phase in ('warmup','read','write'):
            print('k6 phase:',phase,flush=True)
            output = dc('run','--rm','-T','--no-deps','-e','PHASE='+phase,'k6','run','--summary-mode=legacy','/bench/api.js',timeout=60)
            (work/(phase+'.log')).write_text(output)
        print('Warm real retrieval pipeline (64 unmeasured events)',flush=True)
        dc('run','--rm','-T','--no-deps','bench-worker','python','ingest.py','/runbooks')
        dc('up','-d','--wait','bench-worker','bench-publisher')
        deadline = time.monotonic()+120
        query = "from db import connect_db; c=connect_db(); q=c.cursor(); q.execute(\"SELECT count(*) FROM incidentiq_api.diagnoses WHERE mode='RETRIEVAL_ONLY'\"); print(q.fetchone()[0]); c.close()"
        while time.monotonic()<deadline:
            if dc('exec','-T','bench-worker','python','-c',query).strip()=='64':
                break
            time.sleep(1)
        else:
            raise RuntimeError('Warmup pipeline did not drain 64 events')
        dc('stop','bench-publisher')
        conditions['effective_resources']={}
        for service in ('bench-api','bench-worker','bench-publisher','bench-kafka'):
            cid = dc('ps','-aq',service).strip()
            conditions['effective_resources'][service] = json.loads(command(['docker','inspect','--format','{"memory_bytes":{{.HostConfig.Memory}},"nano_cpus":{{.HostConfig.NanoCpus}}}',cid]))
        print('Enqueue fixed 60-event asynchronous batch (publisher stopped)',flush=True)
        output=dc('run','--rm','-T','--no-deps','-e','PHASE=enqueue','k6','run','--summary-mode=legacy','/bench/api.js',timeout=60)
        (work/'enqueue.log').write_text(output)
        with (work/'observer.log').open('w') as log:
            observer=subprocess.Popen(compose+['run','--rm','-T','--no-deps','bench-observer','python','/bench/async_probe.py'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+30
            while not (work/'observer-ready').exists():
                if observer.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError('Observer did not become ready; inspect ignored observer.log')
                time.sleep(0.2)
            print('Measure Kafka append → committed diagnosis visibility',flush=True)
            dc('up','-d','bench-publisher')
            if observer.wait(timeout=150)!=0:
                raise RuntimeError('Async checks failed; inspect async.json and ignored observer.log')
        conditions['memory_after']=memory()
        conditions['total_harness_seconds']=time.monotonic()-started
        conditions['k6_version']=dc('run','--rm','-T','--no-deps','k6','version').strip()
        (results/'conditions.json').write_text(json.dumps(conditions,indent=2)+'\n')
        summary={}
        for phase in ('read','write'):
            data=json.loads((results/(phase+'.json')).read_text())
            metrics=data['metrics']
            latency=metrics['http_req_duration']['values']
            summary[phase]={'requests':metrics['http_reqs']['values']['count'],'requests_per_second':metrics['http_reqs']['values']['rate'],
                            'avg_ms':latency['avg'],'p95_ms':latency['p(95)'],'p99_ms':latency['p(99)'],
                            'error_rate':metrics['http_req_failed']['values']['rate']}
            assert summary[phase]['error_rate']==0
        async_data=json.loads((results/'async.json').read_text())
        summary['async']={k:async_data[k] for k in ('events_per_second','latency','expected','failures','error_rate','window_seconds','max_observer_cycle_ms')}
        (results/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2),flush=True)
        success = True
        print('Measurements retained at',results.relative_to(ROOT),flush=True)
    finally:
        if observer is not None and observer.poll() is None:
            observer.terminate()
            try:
                observer.wait(timeout=5)
            except subprocess.TimeoutExpired:
                observer.kill()
                observer.wait(timeout=5)
        if created:
            # Remove only this fixed benchmark project's temporary containers. No volumes flag.
            command(compose+['down','--timeout','10'],env=env,timeout=60)
            print('Temporary benchmark containers removed; isolated database retained:',name,flush=True)
        (results/'status.json').write_text(json.dumps({'complete':success,'database_retained':created,'finished_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run','cleanup'))
    parser.add_argument('run_id',nargs='?')
    args=parser.parse_args()
    if args.action=='cleanup':
        if not args.run_id:
            parser.error('cleanup requires the exact recorded run ID')
        cleanup(args.run_id)
    else:
        if args.run_id:
            parser.error('run generates a fresh run ID')
        run_benchmarks()
