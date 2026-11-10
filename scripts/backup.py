#!/usr/bin/env python3
"""Run backup tooling only from the explicitly selected Ventic source."""
import runpy
import os
import sys
from deploy import backend_path, target
directory=backend_path(target(os.environ.get('VENTIC_ENVIRONMENT','staging')))/'scripts'
sys.path.insert(0,str(directory))
runpy.run_path(str(directory/'provider-backup.py'),run_name='__main__')
