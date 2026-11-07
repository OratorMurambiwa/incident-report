#!/usr/bin/env python3
"""Render nonsecret Terraform outputs into an ignored Azure overlay; never authenticate/apply."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import uuid
import yaml

ROOT = Path(__file__).resolve().parent.parent


def render(config: dict, release_tag: str, output: Path, example: bool = False) -> None:
    allowed = ROOT/'.incidentiq-backups'/'azure'
    output = output.resolve()
    if not output.is_relative_to(allowed.resolve()) or output == allowed.resolve():
        raise ValueError('Output must be a subdirectory of ignored .incidentiq-backups/azure')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,61}[a-z0-9]', config['namespace']):
        raise ValueError('Invalid namespace')
    if config['namespace'] in ('default','incidentiq-local','kube-system'):
        raise ValueError('Refusing local/system namespace')
    for key in ('tenant_id','client_id'):
        identifier = uuid.UUID(config[key])
        if identifier.int == 0 and not example:
            raise ValueError('Replace example identity identifiers')
    if not re.fullmatch(r'[a-z0-9]{5,50}\.azurecr\.io', config['registry']):
        raise ValueError('Expected an ACR hostname, never credentials or a URL')
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,22}[a-z0-9]', config['key_vault_name']):
        raise ValueError('Invalid Key Vault name')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', release_tag) or release_tag in ('latest','local'):
        raise ValueError('Supply a specific release tag')
    if not example and ('replace' in release_tag or 'replace' in config['registry'] or 'replace' in config['key_vault_name']):
        raise ValueError('Replace all example references')
    source = ROOT/'infra/kubernetes/overlays/azure'
    output.mkdir(parents=True, exist_ok=True)
    for path in source.glob('*.yaml'):
        shutil.copyfile(path, output/path.name)
    def edit(name, change):
        path=output/name;data=yaml.safe_load(path.read_text());change(data)
        path.write_text(yaml.safe_dump(data,sort_keys=False))
    def kustomize(data):
        data['namespace']=config['namespace']
        data['resources'][0]=os.path.relpath(ROOT/'infra/kubernetes/base',output)
        for image in data['images']:
            image['newName']=config['registry']+'/'+image['newName'].split('/')[-1]
            if image['newName'].split('/')[-1].startswith('incidentiq-'):image['newTag']=release_tag
    edit('kustomization.yaml',kustomize)
    edit('namespace.yaml',lambda d:d['metadata'].update(name=config['namespace']))
    edit('serviceaccount.yaml',lambda d:d['metadata']['annotations'].update({'azure.workload.identity/client-id':config['client_id']}))
    edit('secretproviderclass.yaml',lambda d:d['spec']['parameters'].update(clientID=config['client_id'],tenantId=config['tenant_id'],keyvaultName=config['key_vault_name']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--release-tag',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--example',action='store_true',help='Allow documented zero identifiers for static testing only')
    args=parser.parse_args()
    render(json.loads(args.config.read_text()),args.release_tag,args.output,args.example)
    print('Wrote nonsecret overlay; nothing authenticated, pushed or applied')
