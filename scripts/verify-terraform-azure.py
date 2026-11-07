#!/usr/bin/env python3
"""Credential-free Terraform static workflow. Never plan/apply/destroy/login."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
TF=ROOT/'infra/terraform/azure'
BINARY=ROOT/'.incidentiq-backups/terraform/tools/terraform'


def main() -> None:
    if not BINARY.is_file():raise SystemExit('Install checksum-verified Terraform 1.12.2 per docs/azure/README.md')
    # Discard inherited ARM/AZURE variables, CLI config, plugin overrides and HOME caches.
    with tempfile.TemporaryDirectory(prefix='incidentiq-tf-static-') as home:
        config=Path(home)/'terraform.rc';config.write_text('disable_checkpoint = true\n')
        env={'PATH':os.environ['PATH'],'HOME':home,'TF_CLI_CONFIG_FILE':str(config),
             'CHECKPOINT_DISABLE':'1','TF_IN_AUTOMATION':'1','TF_INPUT':'0'}
        for args in (['fmt','-check','-recursive'],['init','-backend=false','-input=false','-lockfile=readonly'],['validate','-no-color']):
            subprocess.run([str(BINARY),'-chdir='+str(TF),*args],env=env,cwd=ROOT,check=True)
    env={'PATH':os.environ['PATH'],'PYTHONPATH':str(ROOT/'.incidentiq-backups/terraform/python-tools')}
    subprocess.run(['python3','-m','unittest','discover','-s','infra/terraform/azure/tests','-v'],cwd=ROOT,env=env,check=True)


if __name__=='__main__':main()
