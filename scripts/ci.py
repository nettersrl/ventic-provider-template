#!/usr/bin/env python3
"""CI entrypoint: verify pinned inputs, then deploy only protected version tags."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from sources import ROOT, check, source_path, provider_version


def run(command, *, cwd=ROOT):
    subprocess.run(list(map(str, command)), cwd=cwd, check=True)


def protected_release(environment):
    expected = 'v' + provider_version(ROOT)
    if os.environ.get('CI_COMMIT_TAG') != expected or os.environ.get('CI_COMMIT_REF_PROTECTED') != 'true':
        raise ValueError('CI deployment requires the matching protected v<provider-version> tag')
    if environment not in ('staging', 'production'): raise ValueError('Unknown environment')
    if (ROOT / 'config/environments' / (environment + '.yaml')).is_file() is False:
        raise ValueError('Provider does not configure that environment')
    status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT, text=True)
    if status: raise ValueError('Provider sources changed after checkout')


def stage_contoso_files(environment):
    # GitLab File variables contain paths, never inline credentials. Additional
    # OpenBao CA/auth material must already be mounted at its configured paths.
    directory = ROOT / 'private' / environment
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    files = {'VENTIC_KUBECONFIG_FILE':'kubeconfig', 'VENTIC_RELEASE_MANIFEST_FILE':'release.json',
             'VENTIC_RELEASE_PUBLIC_KEY_FILE':'release.pub', 'VENTIC_OPENBAO_CONFIG_FILE':'openbao-runtime.json',
             'VENTIC_REGISTRY_TOKEN_FILE':'registry.token', 'VENTIC_LICENSE_KEY_FILE':'license.key'}
    for variable, name in files.items():
        source = os.environ.get(variable)
        if source:
            path=Path(source)
            if path.is_symlink() or not path.is_file(): raise ValueError('CI File variable is not a regular file')
            destination = directory / name
            if destination.is_symlink() or destination.exists(): raise ValueError('Refusing to replace retained private inputs')
            with destination.open('xb') as output:
                os.chmod(destination, 0o600)
                with path.open('rb') as input_file: shutil.copyfileobj(input_file,output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=['verify','deploy'])
    parser.add_argument('--environment', choices=['staging','production'], default='staging')
    args = parser.parse_args()
    os.umask(0o077)
    provider_version(ROOT)
    pins = check()
    backend = source_path('backend')
    frontend = source_path('frontend')
    os.environ['VENTIC_FRONTEND_DIR'] = str(frontend)
    python = backend / '.venv/bin/python'
    if args.action == 'verify':
        run(['make', 'workflow-setup'], cwd=backend)
        run(['npm','ci'], cwd=frontend)
        run(['npm','run','build'], cwd=frontend)
        run([python, backend/'scripts/frontend.py','fetch'], cwd=backend)
        run(['make','check'], cwd=backend)
        run(['make','test-browser'], cwd=backend)
        if (ROOT/'scripts/workflow.py').exists():
            run(['npm','ci']); run(['npm','run','build']); run(['make','test'])
        else: run(['make','test','PYTHON='+str(python)])
        check()
        return
    protected_release(args.environment)
    run(['make','workflow-setup'], cwd=backend)
    run(['npm','ci'], cwd=frontend)
    run([python, backend/'scripts/frontend.py','fetch'], cwd=backend)
    # Deployment reruns checks on the dedicated target runner. Private material
    # is environment scoped; CI has no credential artifacts or broad caches.
    if (ROOT/'scripts/workflow.py').exists():
        if args.environment != 'production': raise ValueError('NI only configures production')
        if not (ROOT/'private/kubeconfig').is_file(): raise ValueError('Mount NI private inputs on the protected deployment runner')
        run(['npm','ci'])
        run([python, ROOT/'scripts/workflow.py','deploy','--version',(ROOT/'VERSION').read_text().strip()])
    else:
        stage_contoso_files(args.environment)
        run([python, ROOT/'scripts/deploy.py','deploy','--environment',args.environment])


if __name__ == '__main__':
    try: main()
    except Exception:
        raise SystemExit('Provider CI stopped; inspect pinned inputs and protected environment settings. Private details suppressed.') from None
