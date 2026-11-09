#!/usr/bin/env python3
"""Run backup tooling only from the explicitly selected Ventic source."""
import runpy
import sys
from sources import source_path
directory=source_path('backend')/'scripts'
sys.path.insert(0,str(directory))
runpy.run_path(str(directory/'provider-backup.py'),run_name='__main__')
