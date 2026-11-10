import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provider_generator', ROOT / 'create-provider.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorTests(unittest.TestCase):
    def test_public_generation_and_existing_provider_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = generator.create('demo', tmp)
            self.assertFalse((target / '.git').exists())
            self.assertEqual(list((target / 'private').iterdir()), [])
            self.assertEqual((target / 'private').stat().st_mode & 0o777, 0o700)
            self.assertIn('company: OWNER_MUST_SUPPLY', (target / 'config/production.yaml').read_text())
            self.assertIn('/brand/demo-dark.svg', (target / 'config/production.yaml').read_text())
            self.assertTrue((target / 'scripts/initialize.py').is_file())
            secret = target / 'private/owner.key'; secret.write_text('synthetic-retained')
            with self.assertRaises(FileExistsError): generator.create('demo', tmp)
            self.assertEqual(secret.read_text(), 'synthetic-retained')

    def test_unlisted_private_state_is_never_read_or_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'template'; source.mkdir()
            for name in generator.FILES:
                p = source / name; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text((ROOT / name).read_text())
            (source / 'private').mkdir(); (source / 'private/secret').write_text('synthetic-private-state')
            (source / '.env').write_text('synthetic-private-environment')
            target = generator.create('demo', tmp, source)
            self.assertFalse((target / '.env').exists())
            self.assertEqual(list((target / 'private').iterdir()), [])

    def test_symlink_refused_before_creating_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'template'; source.mkdir()
            (source / '.dockerignore').symlink_to(ROOT / '.dockerignore')
            with self.assertRaises(ValueError): generator.create('demo', tmp, source)
            self.assertFalse((Path(tmp) / 'ventic-demo-provider').exists())
