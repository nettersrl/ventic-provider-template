#!/usr/bin/env python3
"""Resolve only explicitly locked sources; never follow a branch or scan siblings."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def provider_version(root=ROOT):
    value = (root / 'VERSION').read_text().strip()
    core, separator, suffix = value.partition('-')
    if len(core.split('.')) != 3 or any(not re.fullmatch(r'0|[1-9][0-9]*', part) for part in core.split('.')):
        raise ValueError('Provider VERSION must use SemVer')
    if separator and (not suffix or any(not re.fullmatch(r'[0-9A-Za-z-]+', part) or (part.isdigit() and len(part)>1 and part.startswith('0')) for part in suffix.split('.'))):
        raise ValueError('Invalid SemVer prerelease identifier')
    return value


def lock(root=ROOT):
    data = json.loads((root / 'stack.lock.json').read_text())
    if data.get('format_version') != 1 or set(data['sources']) != {'backend', 'frontend'}:
        raise ValueError('Unsupported stack lock')
    for item in data['sources'].values():
        if not re.fullmatch(r'[0-9a-f]{40}', item['commit']):
            raise ValueError('Sources require full commit pins')
        if not item['repository'].startswith('https://gitlab.com/') or any(x in item['repository'] for x in ('@', '?', '#')):
            raise ValueError('Use permanent HTTPS repository URLs without credentials')
    return data


def source_path(name, root=ROOT):
    data = lock(root)['sources'][name]
    override = os.environ.get('VENTIC_' + name.upper() + '_DIR')
    return Path(override).expanduser().resolve() if override else (root / data['path']).resolve()


def git(path, *args):
    result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('Source Git operation failed; private output suppressed')
    return result.stdout.strip()


def check(root=ROOT, *, clean=True, pins=None, paths=None):
    data = pins or lock(root)
    paths = paths or {name:source_path(name,root) for name in data['sources']}
    for name, item in data['sources'].items():
        path = paths[name]
        if git(path, 'rev-parse', 'HEAD') != item['commit']:
            raise ValueError(name + ' HEAD differs from stack.lock.json')
        if clean and git(path, 'status', '--porcelain', '--untracked-files=normal'):
            raise ValueError(name + ' checkout is dirty; commit/publish and review the pin before releasing')
        if name == 'backend':
            actual = tomllib.loads((path / 'Cargo.toml').read_text())['workspace']['package']['version']
        else:
            actual = json.loads((path / 'package.json').read_text())['version']
        if actual != item['version']:
            raise ValueError(name + ' version differs from stack.lock.json')
        common = git(path, 'rev-parse', 'HEAD:vendor/ventic-common')
        if common != data['common']['commit']:
            raise ValueError('Backend and frontend must use the reviewed common commit')
        if git(path / 'vendor/ventic-common', 'rev-parse', 'HEAD') != common:
            raise ValueError('Initialize the common submodule at its gitlink')
        if clean and git(path / 'vendor/ventic-common', 'status', '--porcelain', '--untracked-files=normal'):
            raise ValueError('Common submodule is dirty')
    backend = paths['backend']
    artifact = json.loads((backend / 'frontend.lock.json').read_text())
    if artifact != data['frontend_artifact']:
        raise ValueError('Frontend artifact differs from the backend reviewed checksum lock')
    contract = json.loads((backend / 'contracts.lock.json').read_text())
    if artifact['contracts'] != contract or data['common']['version'] != contract['version']:
        raise ValueError('Stack contract pins disagree')
    frontend = paths['frontend']
    if json.loads((frontend / 'contracts.lock.json').read_text()) != contract:
        raise ValueError('Frontend and backend contract locks disagree')
    if artifact.get('source_commit') and artifact['source_commit'] != data['sources']['frontend']['commit']:
        raise ValueError('Frontend artifact was built from a different commit')
    if artifact.get('source_dirty'):
        raise ValueError('Production cannot consume a dirty frontend artifact')
    return data


def fetch(root=ROOT):
    for name, item in lock(root)['sources'].items():
        path = source_path(name, root)
        if path.exists():
            if git(path, 'rev-parse', 'HEAD') != item['commit'] or git(path, 'status', '--porcelain'):
                raise ValueError('Refusing to replace an existing source checkout')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(['git', 'clone', '--no-checkout', '--', item['repository'], str(path)], capture_output=True)
            if result.returncode: raise ValueError('Pinned source clone failed; configure runner Git access')
            git(path, 'checkout', '--detach', item['commit'])
        git(path, '-c', 'protocol.file.allow=never', 'submodule', 'update', '--init', '--recursive')
    check(root)



def pin(backend, frontend, root=ROOT):
    data = lock(root)
    paths = {'backend': Path(backend).resolve(), 'frontend': Path(frontend).resolve()}
    for name, path in paths.items():
        data['sources'][name]['commit'] = git(path, 'rev-parse', 'HEAD')
        data['sources'][name]['version'] = (tomllib.loads((path/'Cargo.toml').read_text())['workspace']['package']['version']
                                            if name == 'backend' else json.loads((path/'package.json').read_text())['version'])
    data['common']['commit'] = git(paths['backend'], 'rev-parse', 'HEAD:vendor/ventic-common')
    data['common']['version'] = json.loads((paths['backend']/'contracts.lock.json').read_text())['version']
    data['frontend_artifact'] = json.loads((paths['backend']/'frontend.lock.json').read_text())
    check(root, pins=data, paths=paths)
    (root/'stack.lock.json').write_text(json.dumps(data, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=['fetch', 'check', 'backend', 'frontend', 'pin'])
    parser.add_argument('--backend-dir', type=Path)
    parser.add_argument('--frontend-dir', type=Path)
    args = parser.parse_args()
    if args.action == 'pin' and (not args.backend_dir or not args.frontend_dir):
        parser.error('pin requires --backend-dir and --frontend-dir')
    if args.action == 'pin': pin(args.backend_dir, args.frontend_dir)
    elif args.action == 'fetch': fetch()
    elif args.action == 'check': check(); print('Pinned stack verified')
    else: print(source_path(args.action))


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, OSError):
        raise SystemExit('Pinned stack check failed. Inspect stack.lock.json and source checkouts; private details suppressed.') from None
