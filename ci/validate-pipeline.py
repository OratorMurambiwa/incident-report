"""Offline schema + fail-closed policy validation. Not Azure DevOps server expansion."""
import json
from pathlib import Path
import re
import jsonschema
import yaml

ROOT=Path(__file__).resolve().parent.parent


def policy(pipeline: dict) -> None:
    stages={s['stage']:s for s in pipeline['stages']}
    assert set(stages)=={'Java','Python','React','Infrastructure','DockerSecurity','FutureRelease'}
    release=next(p for p in pipeline['parameters'] if p['name']=='enableRelease')
    assert release['type']=='boolean' and release['default'] is False
    assert set(stages['DockerSecurity']['dependsOn'])=={'Java','Python','React','Infrastructure'}
    condition=stages['FutureRelease']['condition']
    assert all(s in condition for s in ('parameters.enableRelease','refs/heads/main','Manual','succeeded()'))
    release_steps=stages['FutureRelease']['jobs'][0]['steps']
    assert any('exit 1' in s.get('bash','') for s in release_steps)
    for stage in stages.values():
        for job in stage['jobs']:
            for step in job['steps']:
                assert 'continueOnError' not in step
                assert not step.get('task','').startswith(('AzureCLI','AzurePowerShell','Docker@'))
                if step.get('checkout')=='self':assert step['persistCredentials']=='false'
                if step.get('task')=='PublishTestResults@2':
                    assert step['condition']=='succeededOrFailed()'
                    assert step['inputs']['failTaskOnFailedTests'] is True
                    assert step['inputs']['failTaskOnMissingResultsFile'] is True
                for command in re.split(r'\n',step.get('bash','')):
                    assert not re.search(r'\b(?:az login|docker push|kubectl apply|terraform apply|terraform destroy)\b',command)
    db=yaml.safe_load((ROOT/'ci/compose.yaml').read_text())
    assert set(db['services'])=={'postgres'}
    service=db['services']['postgres']
    assert not any(k in service for k in ('ports','volumes','network_mode'))
    assert 'tmpfs' in service and 'healthcheck' in service
    assert service['environment']['POSTGRES_DB']=='incidentiq_api_test'


def validate() -> dict:
    text=(ROOT/'azure-pipelines.yml').read_text()
    # Azure DevOps does not support YAML anchors/aliases.
    assert not any(isinstance(e,(yaml.events.AliasEvent,)) or getattr(e,'anchor',None) for e in yaml.parse(text))
    pipeline=yaml.safe_load(text)
    schema=json.loads((ROOT/'.incidentiq-backups/ci/tools/azure-pipelines-schema.json').read_text())
    # Microsoft's editor schema uses string for Azure-coercible YAML scalars.
    # Preserve native booleans (especially the release default); only schema type checking
    # follows the language service's scalar coercion. Policies above use exact native types.
    checker=jsonschema.Draft7Validator.TYPE_CHECKER.redefine('string',lambda c,v:isinstance(v,(str,int,float,bool)))
    Validator=jsonschema.validators.extend(jsonschema.Draft7Validator,type_checker=checker)
    errors=list(Validator(schema).iter_errors(pipeline))
    if errors:raise AssertionError('Pipeline schema mismatch; inspect YAML/task inputs')
    policy(pipeline)
    return {'schema':'Microsoft official schema with Azure scalar coercion','stages':len(pipeline['stages']),
            'release_default':False,'server_validation_executed':False,'policy':'passed'}


if __name__=='__main__':print(json.dumps(validate(),indent=2))
