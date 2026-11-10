#!/usr/bin/env python3
"""Create a provider from public template files only; never copy runtime state or deploy."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
FILES = (
    '.dockerignore', '.github/workflows/verify.yml', '.gitignore', '.gitlab-ci.yml',
    'AGENTS.md', 'Makefile', 'README.md', 'VERSION', 'requirements-installer.txt', 'stack.lock.json',
    'artwork/portal/contoso.svg', 'artwork/portal/contoso-dark.svg',
    'config/backup.example.json', 'config/distribution.yaml',
    'config/environments/production.yaml', 'config/environments/staging.yaml',
    'config/production.yaml', 'config/sandbox.yaml',
    'scripts/backup.py', 'scripts/binary-release.py', 'scripts/ci-bootstrap.py', 'scripts/ci.py',
    'scripts/deploy.py', 'scripts/initialize.py', 'scripts/provider-version.py', 'scripts/sources.py',
    'tests/test_binary_release.py', 'tests/test_provider.py',
)


def create(abbr, parent, source=ROOT):
    if not re.fullmatch(r'[a-z][a-z0-9]{1,15}', abbr):
        raise ValueError('Use 2–16 lowercase letters/digits, starting with a letter')
    source = Path(source)
    contents = {}
    for name in FILES:
        path = source / name
        if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents if p.is_relative_to(source)):
            raise ValueError('Public template inputs must be regular files without symlinks')
        contents[name] = path.read_text()
    destination = Path(parent).resolve() / ('ventic-' + abbr + '-provider')
    destination.mkdir(exist_ok=False)
    for name, content in contents.items():
        target = destination / name.replace('contoso', abbr)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = re.sub(r'(?m)^(\s*company:\s*)Contoso Ltd\s*$', r'\1OWNER_MUST_SUPPLY', content)
        target.write_text(content.replace('contoso', abbr).replace('Contoso', abbr.upper()))
    (destination / 'private').mkdir(mode=0o700)
    (destination / '.build').mkdir(mode=0o700)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--abbr', required=True)
    parser.add_argument('--parent', type=Path, default=ROOT.parent)
    args = parser.parse_args()
    print(create(args.abbr, args.parent))
    print('Run make init, then supply owner configuration and private inputs. No Git repository or cluster was changed.')


if __name__ == '__main__':
    main()
