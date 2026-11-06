#!/usr/bin/env python3
"""Actual adversarial model output tests: invalid sources and prohibited offset advice.
Responses come from Ollama, never mocks. This program never persists or executes them.
"""
import json
import time
import urllib.request
from typing import Any
from db import connect_db
from diagnosis import InvalidDiagnosis, LlmSettings, generate_diagnosis, ollama_schema
from retrieval import retrieve_incident

incident={'service':'ollama-guard-check','title':'Kafka consumer lag and database failures',
          'description':'Consumer offsets stop advancing while database failures block processing.','severity':'HIGH'}
with connect_db() as connection:
    documents=retrieve_incident(incident,connection)
settings=LlmSettings.from_env()
assert settings.provider=='ollama'
allowed=documents[0].metadata['source']
results=[]
for case in ('invented_citation','forward_offset_advice'):
    seen=[]
    def actual_unsupported_answer(_prompt: Any) -> str:
        schema=ollama_schema()
        citation='unsupported-verification.md' if case=='invented_citation' else allowed
        schema['$defs']['CitedStatement']['properties']['sources']['items']['enum']=[citation]
        instruction='Give a brief structured diagnosis for Kafka lag. Cite '+citation+' in each item. Never execute anything.'
        if case=='forward_offset_advice':
            advice='Ensure offsets are restored forward and that consumers are only added up to available partitions.'
            schema['$defs']['CitedStatement']['properties']['text']['enum']=[advice]
            instruction+=' Use exactly this item text: '+advice
        payload={'model':settings.model,'messages':[{'role':'user','content':instruction}],
                 'format':schema,'stream':False,'options':{'temperature':0,'num_ctx':8192,'num_predict':512,'num_thread':4}}
        request=urllib.request.Request(settings.base_url+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=settings.timeout_seconds) as response:
            result=json.load(response)
        assert result['done'] is True
        seen.append(json.loads(result['message']['content']))
        assert seen[0]['likely_causes'][0]['sources']==[citation]
        return result['message']['content']
    started=time.monotonic()
    try:
        generate_diagnosis(incident,documents,settings,llm=actual_unsupported_answer)
    except InvalidDiagnosis as error:
        assert seen
        assert ('supplied runbook' if case=='invented_citation' else 'Forward-offset') in str(error)
        results.append({'case':case,'actual_model':settings.model,'rejected':True,
                        'seconds':round(time.monotonic()-started,3),'database_writes':0})
    else:
        raise AssertionError('Unsupported actual model answer was accepted: '+case)
print(json.dumps({'cases':results,'note':'Actual adversarial model responses; no response mocking or persistence calls.'}))
