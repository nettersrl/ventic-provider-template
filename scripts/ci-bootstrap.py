#!/usr/bin/env python3
"""Install a non-persistent GitLab job-token credential helper for pinned clones."""
import os
from pathlib import Path

root=Path(__file__).resolve().parents[1]
if os.environ.get('CI_JOB_TOKEN'):
    directory=root/'.build';directory.mkdir(mode=0o700,exist_ok=True)
    helper=directory/'git-askpass.py'
    helper.write_text('''#!/usr/bin/env python3
import os, sys
print('gitlab-ci-token' if 'username' in sys.argv[1].lower() else os.environ['CI_JOB_TOKEN'])
''')
    helper.chmod(0o700)
