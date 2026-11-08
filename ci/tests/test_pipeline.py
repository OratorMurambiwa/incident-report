import copy
import importlib.util
from pathlib import Path
import unittest
import subprocess
import tempfile
import yaml

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pipeline_check',ROOT/'ci/validate-pipeline.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PipelineTests(unittest.TestCase):
    def setUp(self):self.pipeline=yaml.safe_load((ROOT/'azure-pipelines.yml').read_text())
    def stage(self,name):return next(s for s in self.pipeline['stages'] if s['stage']==name)
    def reject(self):
        with self.assertRaises(AssertionError):module.policy(self.pipeline)
    def test_full_schema_and_policies(self):self.assertEqual(module.validate()['stages'],6)
    def test_release_placeholder_fails_closed_without_credentials(self):
        script=self.stage('FutureRelease')['jobs'][0]['steps'][-1]['bash']
        with tempfile.TemporaryDirectory() as home:
            result=subprocess.run(['/bin/bash','-c',script],cwd='/tmp',env={'PATH':'/usr/bin:/bin','HOME':home},capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('Release is intentionally not implemented',result.stdout)
    def test_release_must_default_off(self):self.pipeline['parameters'][0]['default']=True;self.reject()
    def test_release_string_false_is_rejected(self):self.pipeline['parameters'][0]['default']='false';self.reject()
    def test_release_cannot_report_success(self):
        self.stage('FutureRelease')['jobs'][0]['steps'][-1]['bash']='echo release';self.reject()
    def test_no_azure_credential_task(self):
        self.stage('Java')['jobs'][0]['steps'].append({'task':'AzureCLI@2'});self.reject()
    def test_no_image_push(self):
        self.stage('Java')['jobs'][0]['steps'].append({'bash':'docker push example/image'});self.reject()
    def test_security_depends_on_all_checks(self):self.stage('DockerSecurity')['dependsOn']=[];self.reject()
    def test_no_persisted_repository_credential(self):
        self.stage('Java')['jobs'][0]['steps'][0]['persistCredentials']='true';self.reject()
    def test_test_failures_block(self):
        step=next(s for s in self.stage('Java')['jobs'][0]['steps'] if s.get('task')=='PublishTestResults@2')
        step['inputs']['failTaskOnFailedTests']=False;self.reject()


if __name__=='__main__':unittest.main()
