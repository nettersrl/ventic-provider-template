#!/usr/bin/env python3
"""Apply a pinned signed release to a provider-owned Kubernetes API target."""
import argparse
from contextlib import nullcontext
import json
import runpy
import os
from pathlib import Path
import subprocess
import sys

import yaml
from sources import ROOT, check, lock, source_path


def target(environment):
    if environment not in ('staging', 'production'):
        raise ValueError('Unknown environment')
    settings = yaml.safe_load((ROOT / 'config/environments' / (environment + '.yaml')).read_text())
    if settings['transport'] not in ('kubernetes', 'ssh-tunnel'):
        raise ValueError('Unsupported target transport')
    return settings


def inside(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT): raise ValueError('Provider inputs must be inside this repository')
    return path


def plan(settings):
    values = yaml.safe_load(inside(settings['values']).read_text())
    private = inside(settings['privateDirectory'])
    missing = []
    for key in ('context', 'clusterUID'):
        if not settings.get(key) or settings[key].startswith('REPLACE_'): missing.append(key)
    # With `domain`, the verified platform installer derives these hosts/origins.
    # Do not reject the template's unused derived fields before that step.
    public_inputs=json.loads(json.dumps(values))
    if public_inputs.get('domain'):
        public_inputs.pop('domains',None)
        for key in ('portal_url','api_url','marketing_url','docs_url','chat_host'):
            public_inputs.get('provider',{}).pop(key,None)
    if '.example.invalid' in json.dumps(public_inputs) or 'OWNER_MUST_SUPPLY' in json.dumps(public_inputs):
        missing.append('real domains, provider identity and owner-approved legal documents')
    if not values.get('license', {}).get('publicKey'): missing.append('Licman public key')
    if not values.get('ingress', {}).get('trustedProxyCIDRs'): missing.append('inspected ingress proxy CIDRs')
    for key in ('SMTP_HOST', 'SMTP_PORT', 'SMTP_FROM', 'SMTP_USER', 'S3_BUCKET', 'S3_REGION'):
        if not values.get('settings', {}).get(key): missing.append('public setting: ' + key)
    for name in (('kubeconfig', 'openbao-runtime.json') if settings.get('distribution') else ('kubeconfig', 'release.json', 'release.pub', 'openbao-runtime.json')):
        if not (private / name).is_file(): missing.append('private input: ' + name)
    if settings.get('distribution'):
        binary = runpy.run_path(str(ROOT / 'scripts/binary-release.py'))
        trust = inside(binary['settings']()['publicKeyFile'])
        if not trust.is_file(): missing.append('independently trusted release public key')
    return {'ready': not missing, 'missing': missing, 'cluster_modified': False,
            'provider_version': (ROOT / 'VERSION').read_text().strip(), 'stack': {'binary': True} if settings.get('distribution') else lock()}


def backend_path(settings):
    if settings.get('distribution', False):
        return runpy.run_path(str(ROOT / 'scripts/binary-release.py'))['verify']()
    check()
    return source_path('backend')


def execute(action, settings):
    status = plan(settings)
    if not status['ready']: raise ValueError('Complete the deployment plan prerequisites')
    backend = backend_path(settings)
    pins = None if settings.get('distribution', False) else lock()
    sys.path.insert(0, str(backend / 'scripts'))
    import ship
    from deploy_support import tunnel
    from release import verify
    private = inside(settings['privateDirectory'])
    manifest_file = backend / 'release.json' if pins is None else private / 'release.json'
    envelope = json.loads(manifest_file.read_text())
    manifest = verify(envelope, (ROOT / runpy.run_path(str(ROOT / 'scripts/binary-release.py'))['settings']()['publicKeyFile']).read_text().strip() if pins is None else ship.private_file(private / 'release.pub').read_text().strip())
    if pins is not None and (manifest['version'] != pins['sources']['backend']['version'] or manifest.get('frontend') != pins['frontend_artifact']):
        raise ValueError('Signed release differs from the provider stack lock')
    common = [sys.executable, str(backend / 'scripts/ship.py'), 'vps',
              '--context', settings['context'], '--cluster-uid', settings['clusterUID'],
              '--kubeconfig', str(private / 'kubeconfig'), '--values', str(inside(settings['values'])),
              '--release-manifest', str(manifest_file), '--release-public-key-file', str(ROOT / runpy.run_path(str(ROOT / 'scripts/binary-release.py'))['settings']()['publicKeyFile']) if pins is None else str(private / 'release.pub'),
              '--brand-assets-dir', str(ROOT / 'artwork/portal'), '--openbao-config-file', str(private / 'openbao-runtime.json')]
    if action == 'deploy':
        common.append('--apply')
        for name, option in [('registry.token', '--registry-token-file'), ('license.key', '--license-key-file')]:
            if (private / name).exists(): common.extend([option, str(ship.private_file(private / name))])
    tunnel_settings = settings.get('sshTunnel') if settings['transport'] == 'ssh-tunnel' else None
    if settings['transport'] == 'ssh-tunnel' and not tunnel_settings: raise ValueError('SSH tunnel target needs sshTunnel settings')
    with tunnel(private / 'kubeconfig', settings['context'], tunnel_settings):
        # Both actions first perform the signed release, API TLS and cluster checks.
        result = subprocess.run(common, cwd=ROOT, capture_output=True, text=True)
        if result.returncode: raise ValueError('Signed deployment preflight/apply failed; private output suppressed')
        if action == 'verify':
            # ship's plan path verifies TLS configuration; verify the live UID too.
            env = {**os.environ, 'KUBECONFIG': str(private / 'kubeconfig')}
            result = subprocess.run(['kubectl', '--context', settings['context'], 'get', 'namespace', 'kube-system', '-o', 'json'], env=env, capture_output=True, text=True)
            if result.returncode or json.loads(result.stdout)['metadata']['uid'] != settings['clusterUID']:
                raise ValueError('Target cluster UID differs')
            command = [sys.executable, str(backend / 'scripts/providerctl.py'), 'verify', '--context', settings['context'], '--values', str(inside(settings['values'])), '--release-manifest', str(manifest_file), '--release-public-key-file', str(ROOT / runpy.run_path(str(ROOT / 'scripts/binary-release.py'))['settings']()['publicKeyFile']) if pins is None else str(private / 'release.pub')]
            result = subprocess.run(command, env=env, cwd=backend, capture_output=True, text=True)
            if result.returncode: raise ValueError('Rollout verification failed; private output suppressed')
    print('Signed deployment/rollout checks passed. Browser, live payment and inference checks were not run.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=['plan', 'deploy', 'verify', 'private-directory'])
    parser.add_argument('--environment', choices=['staging', 'production'], default='staging')
    args = parser.parse_args()
    os.umask(0o077)
    settings = target(args.environment)
    if args.action == 'private-directory': print(inside(settings['privateDirectory']))
    elif args.action == 'plan': print(json.dumps(plan(settings), indent=2))
    else: execute(args.action, settings)


if __name__ == '__main__':
    try: main()
    except Exception:
        raise SystemExit('Provider action stopped. Inspect public pins/target and private inputs; private details suppressed.') from None
