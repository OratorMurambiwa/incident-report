"""Offline parsed-HCL and Kubernetes security contract checks. No Azure SDK/credentials."""
import importlib.util
import ipaddress
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import hcl2
import yaml

ROOT = Path(__file__).resolve().parents[4]
TF = ROOT/'infra/terraform/azure'


def load(path):
    with (TF/path).open() as handle: return hcl2.load(handle)


def resources(path):
    result = {}
    for block in load(path).get('resource', []):
        for kind, body in block.items():
            result.setdefault(kind, {}).update(body)
    return result


class AzureStaticTests(unittest.TestCase):
    def test_modular_root_and_provider_pin(self):
        modules = {k for b in load('main.tf')['module'] for k in b}
        self.assertEqual(modules, {'aks','network','registry','identities','vault'})
        version = load('versions.tf')['terraform'][0]
        self.assertEqual(version['required_providers'][0]['azurerm']['version'], '= 4.30.0')
        self.assertTrue((TF/'.terraform.lock.hcl').is_file())

    def test_private_aks_identity_and_access(self):
        aks=resources('modules/aks/main.tf')['azurerm_kubernetes_cluster']['this']
        for key in ('private_cluster_enabled','local_account_disabled','role_based_access_control_enabled','oidc_issuer_enabled','workload_identity_enabled'):
            self.assertIs(aks[key],True,key)
        self.assertIs(aks['private_cluster_public_fqdn_enabled'],False)
        self.assertEqual(aks['identity'][0]['type'],'UserAssigned')
        self.assertIs(aks['azure_active_directory_role_based_access_control'][0]['azure_rbac_enabled'],True)
        self.assertIs(aks['key_vault_secrets_provider'][0]['secret_rotation_enabled'],True)
        self.assertEqual(aks['sku_tier'],'Free')

    def test_registry_has_no_password_or_anonymous_auth(self):
        acr=resources('modules/registry/main.tf')['azurerm_container_registry']['this']
        self.assertIs(acr['admin_enabled'],False)
        self.assertIs(acr['anonymous_pull_enabled'],False)
        self.assertEqual(acr['sku'],'Basic')

    def test_private_rbac_vault_and_retention(self):
        rs=resources('modules/vault/main.tf');vault=rs['azurerm_key_vault']['this']
        self.assertIs(vault['enable_rbac_authorization'],True)
        self.assertIs(vault['public_network_access_enabled'],False)
        self.assertIs(vault['purge_protection_enabled'],True)
        self.assertEqual(vault['soft_delete_retention_days'],90)
        self.assertEqual(vault['network_acls'][0]['default_action'],'Deny')
        self.assertEqual(rs['azurerm_role_assignment']['read_secrets']['scope'],'${azurerm_key_vault.this.id}')
        self.assertIn('azurerm_private_endpoint',rs)
        self.assertIn('azurerm_private_dns_zone_virtual_network_link',rs)

    def test_scoped_roles_and_federation(self):
        rs=resources('main.tf');roles=rs['azurerm_role_assignment']
        self.assertEqual({b['role_definition_name'] for b in roles.values()}, {'AcrPull','Network Contributor','Managed Identity Operator'})
        self.assertEqual(roles['registry_pull']['scope'],'${module.registry.id}')
        self.assertEqual(roles['node_network']['scope'],'${module.network.aks_subnet_id}')
        fic=rs['azurerm_federated_identity_credential']['keyvault']
        self.assertEqual(fic['audience'],['api://AzureADTokenExchange'])
        self.assertEqual(fic['subject'],'system:serviceaccount:${var.kubernetes_namespace}:incidentiq-keyvault')
        self.assertEqual(fic['issuer'],'${module.aks.oidc_issuer_url}')

    def test_cidrs_are_isolated_and_nonoverlapping(self):
        net=resources('modules/network/main.tf')
        subnets=[ipaddress.ip_network(v['address_prefixes'][0]) for v in net['azurerm_subnet'].values()]
        aks=resources('modules/aks/main.tf')['azurerm_kubernetes_cluster']['this']['network_profile'][0]
        networks=subnets+[ipaddress.ip_network(aks[k]) for k in ('pod_cidr','service_cidr')]
        for i,a in enumerate(networks):
            for b in networks[i+1:]: self.assertFalse(a.overlaps(b),(a,b))

    def test_no_cloud_data_sources_or_secret_values(self):
        for path in TF.rglob('*.tf'):
            with path.open() as handle:data=hcl2.load(handle)
            self.assertNotIn('data',data,str(path))
            for block in data.get('resource',[]):
                self.assertNotIn('azurerm_key_vault_secret',block)
                self.assertNotIn('random_password',block)
            for block in data.get('output',[]):
                self.assertFalse(any(k in ('kube_config','kube_admin_config','password','client_secret') for k in block))
        provider=load('versions.tf')['provider'][0]['azurerm']
        self.assertIs(provider['use_cli'],False)
        self.assertIs(provider['use_msi'],False)
        self.assertEqual(provider['resource_provider_registrations'],'none')

    def test_state_values_and_plans_ignored_but_lock_retained(self):
        for name in ('private.tfvars','private.tfvars.json','terraform.tfstate','terraform.tfstate.backup','private.tfplan','.terraform/providers/test'):
            r=subprocess.run(['git','check-ignore','--quiet',str(TF/name)],cwd=ROOT)
            self.assertEqual(r.returncode,0,name)
        self.assertEqual(subprocess.run(['git','check-ignore','--quiet',str(TF/'.terraform.lock.hcl')],cwd=ROOT).returncode,1)

    def test_azure_csi_wiring_for_all_secret_consumers(self):
        raw=subprocess.check_output(['kubectl','kustomize','infra/kubernetes/overlays/azure'],cwd=ROOT,text=True)
        docs=list(yaml.safe_load_all(raw));objects={(d['kind'],d['metadata']['name']):d for d in docs}
        self.assertNotIn('Secret',{d['kind'] for d in docs})
        spc=objects['SecretProviderClass','incidentiq-keyvault']['spec']
        self.assertEqual(spc['provider'],'azure')
        self.assertEqual(spc['parameters']['usePodIdentity'],'false')
        self.assertEqual({v['key'] for v in spc['secretObjects'][0]['data']},{'POSTGRES_USER','POSTGRES_PASSWORD'})
        consumers=0
        for d in docs:
            if d['kind'] not in ('Deployment','StatefulSet','Job'):continue
            template=d['spec']['template'];pod=template['spec']
            if not any('secretRef' in e for c in pod['containers'] for e in c.get('envFrom',[])):continue
            consumers+=1
            self.assertEqual(pod['serviceAccountName'],'incidentiq-keyvault')
            self.assertEqual(template['metadata']['labels']['azure.workload.identity/use'],'true')
            self.assertTrue(any(v.get('csi',{}).get('driver')=='secrets-store.csi.k8s.io' for v in pod['volumes']))
            for c in pod['containers']+pod.get('initContainers',[]):
                self.assertTrue(any(v['name']=='keyvault' for v in c.get('volumeMounts',[])))
        self.assertEqual(consumers,5)
        for name in ('postgres','kafka'):
            claim=objects['StatefulSet',name]['spec']['volumeClaimTemplates'][0]['spec']
            self.assertEqual(claim['storageClassName'],'managed-csi')
            self.assertEqual(claim['resources']['requests']['storage'],'8Gi')

    def test_renderer_rejects_placeholders_and_repo_overwrite(self):
        spec=importlib.util.spec_from_file_location('render',ROOT/'scripts/render-azure-overlay.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        config=json.loads((ROOT/'docs/azure/kustomize-config.example.json').read_text())
        with self.assertRaises(ValueError):module.render(config,'release-abc',ROOT/'infra/kubernetes/overlays/local',True)
        with self.assertRaises(ValueError):module.render(config,'release-abc',ROOT/'.incidentiq-backups/azure/test')
        config['namespace']='incidentiq-local'
        with self.assertRaises(ValueError):module.render(config,'release-abc',ROOT/'.incidentiq-backups/azure/test',True)


if __name__=='__main__':unittest.main()
