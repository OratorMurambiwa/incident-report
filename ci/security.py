"""Blocking credential/config checks; vulnerability inventory is a separate advisory report."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent.parent
PATTERNS={
    'private key':r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'GitHub token':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'Azure/account secret assignment':r'(?i)(?:client_secret|account_key|sas_token)\s*[=:]\s*["\'][A-Za-z0-9+/=._-]{20,}["\']',
    'AWS credential':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
}


def check_source() -> int:
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    files={p for p in raw.decode().split('\0') if p}
    for name in files:
        path=ROOT/name
        if not path.is_file():continue
        data=path.read_text(errors='replace')
        for rule,pattern in PATTERNS.items():
            if re.search(pattern,data):
                raise AssertionError('Potential '+rule+' in '+name+' (value intentionally withheld)')
        assert path.name!='.env' and not path.name.endswith(('.tfstate','.tfvars','.tfplan')),name
    return len(files)


def check_image(image: str) -> dict:
    config=json.loads(subprocess.check_output(['docker','image','inspect',image,'--format','{{json .Config}}'],text=True))
    for entry in config.get('Env',[]):
        name,_,value=entry.partition('=')
        if re.search(r'(?i)(password|client_secret|account_key|sas_token|access_token)',name):
            assert not value,'Credential-like baked environment field: '+name
    if 'worker' in image or 'api' in image:
        assert config.get('User') not in (None,'','root','0'),'Runtime must use existing nonroot app user'
    return {'image':image,'user':config.get('User'),'baked_credential_check':'passed'}


if __name__=='__main__':
    import sys
    print(json.dumps({'source_files':check_source(),'images':[check_image(i) for i in sys.argv[1:]],
                      'note':'Pattern checks are not a guarantee that all secrets are detected.'},indent=2))
