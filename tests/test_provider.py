"""Offline safety and release pin regressions; no cluster or customer inputs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import sources
import deploy
import ci


class ProviderTests(unittest.TestCase):
    def test_domain_override_ignores_unused_template_hosts_in_offline_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            values=root/'values.yaml'
            values.write_text('domain: demo.example.org\nprovider:\n  portal_url: https://portal.contoso.example.invalid\n  support_email: support@example.org\ndomains:\n  api: api.contoso.example.invalid\nlicense:\n  publicKey: trusted\ningress:\n  trustedProxyCIDRs: [192.0.2.0/24]\n')
            settings={'values':'values.yaml','privateDirectory':'private','context':'explicit','clusterUID':'owned','distribution':True}
            with patch.object(deploy,'inside',side_effect=lambda value:root/value):
                status=deploy.plan(settings)
            self.assertNotIn('real domains, provider identity and owner-approved legal documents',status['missing'])

    def test_template_plan_is_offline_and_incomplete(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('No external commands')):
            plan=deploy.plan(deploy.target('staging'))
        self.assertFalse(plan['ready'])
        self.assertFalse(plan['cluster_modified'])
        self.assertIn('clusterUID',plan['missing'])
        self.assertIn('real domains, provider identity and owner-approved legal documents',plan['missing'])

    def test_environment_and_path_escape_refused(self):
        for name in ('../production','other','production.yaml'):
            with self.assertRaises(ValueError):deploy.target(name)
        with self.assertRaises(ValueError):deploy.inside('../private')

    def test_protected_matching_tag_required_before_deployment(self):
        for env in ({}, {'CI_COMMIT_TAG':'v0.1.0','CI_COMMIT_REF_PROTECTED':'false'},
                    {'CI_COMMIT_TAG':'v9.0.0','CI_COMMIT_REF_PROTECTED':'true'}):
            with patch.dict(os.environ,env,clear=True), self.assertRaises(ValueError):ci.protected_release('production')

    def test_pins_are_full_commits_and_no_credentials_or_runtime(self):
        data=sources.lock()
        self.assertEqual(set(data['sources']),{'backend','frontend'})
        for value in data['sources'].values():
            self.assertRegex(value['commit'],r'^[a-f0-9]{40}$')
            self.assertNotIn('@',value['repository'])
        self.assertEqual(len(data['frontend_artifact']['bundle_sha256']),64)
        self.assertFalse((ROOT/'private').exists())

    def test_refuse_dirty_and_wrong_commit_before_consuming_sources(self):
        pins=sources.lock()
        paths={name:Path('/synthetic')/name for name in pins['sources']}
        with patch.object(sources,'git',return_value='wrong'), self.assertRaisesRegex(ValueError,'HEAD differs'):
            sources.check(pins=pins,paths=paths)
        def git(path,*args):
            return pins['sources'][path.name]['commit'] if args==('rev-parse','HEAD') else ' M source'
        with patch.object(sources,'git',side_effect=git), self.assertRaisesRegex(ValueError,'dirty'):
            sources.check(pins=pins,paths=paths)

    def test_pin_update_validates_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'stack.lock.json').write_text((ROOT/'stack.lock.json').read_text())
            before=(root/'stack.lock.json').read_bytes()
            with self.assertRaises(ValueError):sources.pin(root/'missing-backend',root/'missing-frontend',root)
            self.assertEqual(before,(root/'stack.lock.json').read_bytes())

    def test_incomplete_template_cannot_deploy(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('No remote commands')), self.assertRaises(ValueError):
            deploy.execute('deploy',deploy.target('production'))

    def test_ci_files_are_paths_and_do_not_replace_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'job-file';source.write_text('synthetic-file-content')
            with patch.object(ci,'ROOT',root), patch.dict(os.environ,{'VENTIC_KUBECONFIG_FILE':str(source)},clear=True):
                ci.stage_contoso_files('staging')
                target=root/'private/staging/kubeconfig'
                self.assertEqual(target.stat().st_mode & 0o777,0o600)
                self.assertEqual(target.read_text(),'synthetic-file-content')
                with self.assertRaises(ValueError):ci.stage_contoso_files('staging')


if __name__=='__main__':unittest.main()
