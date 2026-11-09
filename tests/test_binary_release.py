"""Exercise signed binary acquisition without network or platform source access."""
import base64
import hashlib
import io
import json
from pathlib import Path
import runpy
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[1]
binary = runpy.run_path(str(ROOT / 'scripts/binary-release.py'))


class BinaryReleaseTests(unittest.TestCase):
    def fixture(self, root, escaped=False):
        key = Ed25519PrivateKey.from_private_bytes(bytes([31]) * 32)
        encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip('=')
        (root / 'private').mkdir()
        (root / 'private/release.pub').write_text(encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)))
        (root / 'config').mkdir()
        (root / 'config/distribution.yaml').write_text('version: 1.0.0\norigin: https://synthetic.invalid\npublicKeyFile: private/release.pub\n')
        catalog = json.dumps({'version': 'v1.0.0', 'artifacts': []}).encode()
        files = {'services/control/src/remote-agent-release.json': catalog,
                 '../escape' if escaped else 'scripts/providerctl.py': b'# synthetic installer'}
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for name, data in files.items():
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
        artifacts = {'ventic-1.0.0.tar.gz': buffer.getvalue(), 'manifest.json': catalog}
        manifest = {'product': 'netter-ai-platform', 'license_mode': 'enforced', 'distribution_format': 1,
                    'platform': 'linux/amd64', 'version': '1.0.0',
                    'installer_files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
                    'artifacts': {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()}}
        signature = key.sign(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())
        artifacts['release.json'] = json.dumps({'manifest': manifest, 'signature': encode(signature)}).encode()
        return artifacts

    def fetch(self, root, artifacts):
        def download(url, path, expected=None, limit=None):
            content = artifacts[url.rsplit('/', 1)[1]]
            if expected and hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('Release artifact checksum mismatch')
            Path(path).write_bytes(content)
        with patch.dict(binary['fetch'].__globals__, {'download': download}):
            return binary['fetch'](root)

    def test_signed_package_downloads_and_rechecks_cached_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = self.fetch(root, self.fixture(root))
            self.assertEqual((target / 'scripts/providerctl.py').read_bytes(), b'# synthetic installer')
            self.assertFalse((root / '.build/sources').exists())
            (target / 'scripts/providerctl.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'differs'):
                binary['verify'](root)

    def test_signed_archive_cannot_escape_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'Invalid installer'):
                self.fetch(root, self.fixture(root, escaped=True))
            self.assertFalse((root / 'escape').exists())

    def test_checksum_failure_does_not_publish_partial_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = self.fixture(root)
            artifacts['ventic-1.0.0.tar.gz'] = b'corrupt'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                self.fetch(root, artifacts)
            self.assertFalse((root / '.build/releases/1.0.0').exists())
