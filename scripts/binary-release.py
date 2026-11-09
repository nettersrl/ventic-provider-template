#!/usr/bin/env python3
"""Fetch a signed Ventic installer without fetching or compiling platform sources."""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from urllib.parse import urlsplit
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def download(url, destination, expected=None, limit=1024**3):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use permanent credential-free HTTPS release URLs')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    digest = hashlib.sha256()
    total = 0
    with http.open(url, timeout=120) as response, Path(destination).open('xb') as output:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > limit: raise ValueError('Release artifact exceeds size limit')
            digest.update(chunk)
            output.write(chunk)
    if expected and digest.hexdigest() != expected: raise ValueError('Release artifact checksum mismatch')


def settings(root=ROOT):
    import yaml
    config = yaml.safe_load((root / 'config/distribution.yaml').read_text())
    if set(config) != {'version', 'origin', 'publicKeyFile'} or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?', config['version']):
        raise ValueError('Invalid binary release configuration')
    return config


def verified_manifest(envelope, key):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    decode = lambda value: base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    raw = json.dumps(envelope['manifest'], sort_keys=True, separators=(',', ':')).encode()
    Ed25519PublicKey.from_public_bytes(decode(key)).verify(decode(envelope['signature']), raw)
    manifest = envelope['manifest']
    if (manifest.get('product') != 'netter-ai-platform' or manifest.get('license_mode') != 'enforced'
            or manifest.get('distribution_format') != 1 or manifest.get('platform') != 'linux/amd64'):
        raise ValueError('A licensed Linux amd64 binary release is required')
    for name, digest in manifest['artifacts'].items():
        if PurePosixPath(name).name != name or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Invalid artifact inventory')
    return manifest


def fetch(root=ROOT):
    config = settings(root)
    public_key = (root / config['publicKeyFile']).read_text().strip()
    target = root / '.build/releases' / config['version']
    if target.exists():
        return verify(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ventic-release-', dir=target.parent) as temporary:
        staging = Path(temporary)
        prefix = config['origin'].rstrip('/') + '/releases/' + config['version'] + '/'
        manifest_file = staging / 'release.json'
        download(prefix + 'release.json', manifest_file, limit=4 * 1024 * 1024)
        manifest = verified_manifest(json.loads(manifest_file.read_text()), public_key)
        if manifest['version'] != config['version']: raise ValueError('Release version differs from requested version')
        name = 'ventic-' + config['version'] + '.tar.gz'
        bundle = staging / name
        download(prefix + name, bundle, manifest['artifacts'][name])
        installer = staging / 'installer'
        installer.mkdir()
        with tarfile.open(bundle, 'r:gz') as archive:
            entries = archive.getmembers()
            if len(entries) > 25000 or sum(entry.size for entry in entries) > 1024**3:
                raise ValueError('Installer is too large')
            names = set()
            for entry in entries:
                path = PurePosixPath(entry.name)
                if (not entry.isfile() or path.is_absolute() or '..' in path.parts or '\\' in entry.name
                        or str(path) != entry.name or entry.name in names
                        or entry.name not in manifest['installer_files']):
                    raise ValueError('Invalid installer member')
                names.add(entry.name)
                content = archive.extractfile(entry).read()
                if hashlib.sha256(content).hexdigest() != manifest['installer_files'][entry.name]:
                    raise ValueError('Installer member checksum mismatch')
                destination = installer / entry.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            if names != set(manifest['installer_files']): raise ValueError('Installer member inventory differs')
        # Native agent downloads are public signed-release artifacts, not sources.
        catalog_file = installer / 'services/control/src/remote-agent-release.json'
        catalog = json.loads(catalog_file.read_text())
        cache = installer / 'data/remote-agent' / catalog['version']
        cache.mkdir(parents=True)
        native_names = {entry['filename'] for entry in catalog['artifacts']} | {'manifest.json'}
        if catalog.get('update'):
            native_names |= {'update.json'} | {name for name in manifest['artifacts'] if name.startswith('ventic-remote-agent-') and name.endswith('.bin')}
        for native in sorted(native_names):
            download(prefix + native, cache / native, manifest['artifacts'][native])
        shutil.copyfile(manifest_file, installer / 'release.json')
        shutil.move(installer, target)
    return verify(root)


def verify(root=ROOT):
    config = settings(root)
    target = root / '.build/releases' / config['version']
    manifest = verified_manifest(json.loads((target / 'release.json').read_text()),
                                 (root / config['publicKeyFile']).read_text().strip())
    if manifest['version'] != config['version']: raise ValueError('Release version differs')
    for name, expected in manifest['installer_files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('Invalid signed installer member')
        file = target / name
        if file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError('Installed release differs from signed inventory')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fetch', 'verify', 'path'))
    args = parser.parse_args()
    try:
        print(fetch() if args.action == 'fetch' else verify())
    except Exception:
        raise SystemExit('Binary release verification failed; check public version, trust key and release availability.') from None
