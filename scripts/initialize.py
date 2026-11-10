#!/usr/bin/env python3
"""Prepare a private local workspace without generating owner inputs or deploying."""
import argparse
import json
import os
from pathlib import Path

from sources import ROOT
import deploy


def prepare(root, private):
    root = Path(root).resolve()
    private = Path(os.path.abspath(private))
    relative = private.relative_to(root / 'private')
    directories = [root / '.build', root / 'private']
    current = root / 'private'
    for part in relative.parts:
        current = current / part
        directories.append(current)
    for directory in directories:
        if directory.is_symlink():
            raise ValueError('Private workspace directories must not be symlinks')
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--environment', choices=('staging', 'production'), default='staging')
    args = parser.parse_args()
    settings = deploy.target(args.environment)
    prepare(ROOT, ROOT / settings['privateDirectory'])
    print(json.dumps({'local_workspace_initialized': True, 'cluster_modified': False,
                      'deployment': deploy.plan(settings)}, indent=2))


if __name__ == '__main__':
    main()
