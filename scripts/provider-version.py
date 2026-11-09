#!/usr/bin/env python3
"""Set the provider deployment version; never change upstream source pins implicitly."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', required=True)
args = parser.parse_args()
value = args.version
if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?', value):
    raise SystemExit('Use MAJOR.MINOR.PATCH[-prerelease]')
if '-' in value and any(part.isdigit() and len(part)>1 and part.startswith('0') for part in value.split('-',1)[1].split('.')):
    raise SystemExit('SemVer numeric prerelease identifiers cannot have leading zeroes')
(ROOT / 'VERSION').write_text(value + '\n')
for chart in (ROOT / 'charts').glob('*/Chart.yaml'):
    text = re.sub(r'^(version|appVersion):.*$', lambda match: match[1] + ': ' + value, chart.read_text(), flags=re.M)
    chart.write_text(text)
if (ROOT / 'package.json').exists():
    file = ROOT / 'package.json'; data=json.loads(file.read_text()); data['version']=value
    file.write_text(json.dumps(data,indent=2)+'\n')
    file = ROOT / 'package-lock.json'; data=json.loads(file.read_text()); data['version']=value; data['packages']['']['version']=value
    file.write_text(json.dumps(data,indent=2)+'\n')
print(value)
