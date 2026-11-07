"""Negative tests for isolation and cross-resource manifest validation."""
import copy
import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT = Path('/repo')
spec = importlib.util.spec_from_file_location('validation', ROOT/'scripts/validate-kubernetes.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.docs = list(yaml.safe_load_all((ROOT/'.incidentiq-backups/kubernetes/rendered.yaml').read_text()))

    def resource(self, kind, name):
        return next(d for d in self.docs if d['kind']==kind and d['metadata']['name']==name)

    def config(self):
        return next(d['data'] for d in self.docs if d['kind']=='ConfigMap' and d['metadata']['name'].startswith('incidentiq-config-'))

    def rejected(self):
        with self.assertRaises(AssertionError): validation.validate(self.docs)

    def test_valid_overlay(self):
        self.assertEqual(validation.validate(self.docs)['resources'],17)

    def test_reject_normal_database(self):
        self.config()['POSTGRES_DB']='incidentiq';self.rejected()

    def test_reject_host_volume(self):
        self.resource('Deployment','worker')['spec']['template']['spec']['volumes'].append({'name':'unsafe','hostPath':{'path':'/var/lib/docker/volumes'}});self.rejected()

    def test_reject_bad_service_port(self):
        self.resource('Service','api')['spec']['ports'][0]['targetPort']=9999;self.rejected()

    def test_reject_missing_probe(self):
        del self.resource('Deployment','worker')['spec']['template']['spec']['containers'][0]['livenessProbe'];self.rejected()

    def test_reject_hosted_or_generative_provider(self):
        self.config()['LLM_PROVIDER']='ollama';self.rejected()

    def test_reject_publisher_migration(self):
        c=self.resource('Deployment','publisher')['spec']['template']['spec']['containers'][0]
        c['env']=[e for e in c['env'] if e['name']!='SPRING_FLYWAY_ENABLED'];self.rejected()

    def test_reject_kafka_dns_deadlock(self):
        self.resource('Service','kafka')['spec']['publishNotReadyAddresses']=False;self.rejected()

    def test_reject_missing_configmap(self):
        self.resource('Deployment','worker')['spec']['template']['spec']['volumes'][0]['configMap']['name']='missing';self.rejected()


if __name__=='__main__': unittest.main()
