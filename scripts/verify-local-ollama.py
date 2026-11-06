#!/usr/bin/env python3
"""Verify real local Ollama flows; restore the base retrieval-only worker even on failure.
Requires the selected model to have been explicitly pulled already. Never executes suggestions.
"""
import json
import re
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / '.incidentiq-backups' / 'ollama-verification'
EVIDENCE.mkdir(parents=True, exist_ok=True)
OVERRIDE = EVIDENCE / 'negative.json'


def compose(*args: str, local: bool = True, negative: bool = False) -> str:
    command = ['docker','compose','-f','compose.yaml']
    if local:
        command += ['-f','compose.ollama.yaml']
    if negative:
        command += ['-f',str(OVERRIDE)]
    return subprocess.check_output(command + list(args), cwd=ROOT, text=True, stderr=subprocess.STDOUT)


def observation(incident_id: str) -> dict[str, Any]:
    code = '''
import json,sys
from db import connect_db
from kafka import KafkaConsumer,TopicPartition
id=sys.argv[1]
with connect_db() as c, c.cursor() as q:
 q.execute("""SELECT json_build_object('status',i.status,
 'outbox',(SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id=i.id),
 'published',(SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id=i.id AND published_at IS NOT NULL),
 'receipts',(SELECT count(*) FROM incidentiq_api.processed_events WHERE incident_id=i.id),
 'snapshots',(SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE incident_id=i.id),
 'diagnoses',(SELECT count(*) FROM incidentiq_api.diagnoses WHERE incident_id=i.id))
 FROM incidentiq_api.incidents i WHERE id=%s""",(id,))
 row=q.fetchone()[0]
 q.execute("SELECT partition_id,offset_id,error_code,attempts FROM incidentiq_api.failed_events WHERE position(convert_to(%s,'UTF8') IN payload)>0",(id,))
 failures=q.fetchall()
 row['failures']=[dict(zip(('partition','offset','error','attempts'),f)) for f in failures]
consumer=KafkaConsumer(bootstrap_servers='kafka:29092',group_id='incidentiq-worker-v1',enable_auto_commit=False)
for failure in row['failures']:
 failure['committed_offset']=consumer.committed(TopicPartition('incident.created',failure['partition']))
consumer.close(autocommit=False)
print(json.dumps(row))
'''
    return json.loads(subprocess.check_output(['docker','compose','exec','-T','worker','python','-c',code,incident_id],cwd=ROOT,text=True))


def negative_case(name: str, model: str, timeout: int) -> dict[str, Any]:
    OVERRIDE.write_text(json.dumps({'services':{'worker':{'environment':{'OLLAMA_MODEL':model,'OLLAMA_TIMEOUT_SECONDS':str(timeout)}}}}))
    compose('up','-d','--no-deps','--wait','worker',negative=True)
    payload={'service':'ollama-negative','title':'Verification '+name+' '+str(uuid.uuid4())[:8],
             'description':'PostgreSQL connection pool exhausted, too many clients, SQLSTATE 08006. Inspect connection concurrency.', 'severity':'HIGH'}
    request=urllib.request.Request('http://127.0.0.1:5173/api/incidents',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:
        incident=json.load(response)
        assert response.status==201
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        row=observation(incident['id'])
        if row['status']=='FAILED' and row['failures'] and all(f['committed_offset'] is not None and f['committed_offset']>f['offset'] for f in row['failures']):
            break
        time.sleep(1)
    else:
        raise AssertionError((name,'did not reach durable FAILED with committed offset',row))
    assert row['outbox']==row['published']==1
    assert row['receipts']==row['snapshots']==row['diagnoses']==0
    assert len(row['failures'])==1 and row['failures'][0]['error']=='ModelUnavailable' and row['failures'][0]['attempts']==3
    print('PASS real',name,incident['id'],json.dumps(row),flush=True)
    return {'case':name,'incident_id':incident['id'],**row}


def main() -> None:
    report={'model':'qwen3:0.6b','runtime':'0.6.8','negative_cases':[]}
    assert compose('exec','-T','worker','printenv','LLM_PROVIDER',local=False).strip()=='none', 'Start with base retrieval-only worker'
    compose('config','--quiet')
    try:
        compose('up','-d','--no-deps','--wait','ollama','worker')
        version=compose('exec','-T','worker','python','-c',"import urllib.request;print(urllib.request.urlopen('http://ollama:11434/api/version',timeout=5).read().decode())")
        report['version']=json.loads(version)
        postgres_id=compose('ps','-q','postgres').strip()
        project=subprocess.check_output(['docker','inspect','--format','{{ index .Config.Labels "com.docker.compose.project" }}',postgres_id],text=True).strip()
        command=['docker','run','--rm','--network',project+'_default','--ipc=host',
                 '-v',str(ROOT/'scripts/verify-ollama-browser.py')+':/verify.py:ro',
                 '-v',str(EVIDENCE)+':/evidence','--entrypoint','python','incidentiq-browser:local','/verify.py']
        subprocess.run(command,cwd=ROOT,check=True)
        generated=json.loads((EVIDENCE/'generated.json').read_text())
        worker_logs=compose('logs','--no-color','worker')
        (EVIDENCE/'generation-worker.log').write_text(worker_logs)
        report['generation_seconds']=[float(value) for value in re.findall(r'ollama_generation seconds=([0-9.]+)',worker_logs)]
        metadata=compose('exec','-T','worker','python','-c',"import json,urllib.request;print(json.dumps({k:json.load(urllib.request.urlopen('http://ollama:11434/api/'+k,timeout=5)) for k in ('tags','ps')}))")
        report['model_metadata']=json.loads(metadata)
        report['positive_cases']=[]
        for item in generated['results']:
            row=observation(item['incident_id'])
            assert row['status']=='DIAGNOSED' and row['outbox']==row['published']==row['receipts']==row['diagnoses']==1 and row['snapshots']==5 and not row['failures']
            report['positive_cases'].append({'case':item['case'],'incident_id':item['incident_id'],'end_to_end_seconds':item['end_to_end_seconds'],**row})
        assert len(report['positive_cases']) >= 2
        report['rejected_actual_kafka_answers']=[]
        for item in generated.get('rejections',[]):
            row=observation(item['incident_id'])
            assert row['status']=='FAILED' and row['outbox']==row['published']==1
            assert row['receipts']==row['snapshots']==row['diagnoses']==0
            assert len(row['failures'])==1 and row['failures'][0]['error']=='InvalidDiagnosis' and row['failures'][0]['attempts']==3
            assert row['failures'][0]['committed_offset']>row['failures'][0]['offset']
            report['rejected_actual_kafka_answers'].append({**item,**row})
        with (ROOT/'scripts/verify-ollama-guards.py').open() as source:
            guard_output=subprocess.check_output(['docker','compose','exec','-T','worker','python','-'],cwd=ROOT,stdin=source,text=True)
        report['unsupported_answer']=json.loads(guard_output)
        print('PASS unsupported actual model answer rejected:',guard_output.strip(),flush=True)
        report['negative_cases'].append(negative_case('unavailable model' ,'incidentiq-not-installed:verification',30))
        compose('exec','-T','ollama','ollama','stop','qwen3:0.6b')
        report['negative_cases'].append(negative_case('one-second timeout','qwen3:0.6b',1))
    finally:
        compose('up','-d','--no-deps','--wait','worker',local=False)
        assert compose('exec','-T','worker','printenv','LLM_PROVIDER',local=False).strip()=='none'
        print('Restored base retrieval-only worker; data and volumes retained.',flush=True)
    report['retrieval_only_restored']=True
    report['semantic_review_required']=True
    report['semantic_grounding_verified']=False
    (EVIDENCE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print("Transport/schema/failure checks complete. Semantic grounding is NOT certified; manually review answers before publication.")


if __name__=='__main__':
    main()
