#!/usr/bin/env python

import json
import subprocess

data = json.loads(subprocess.check_output(['storcli', '/call/eall/sall', 'show', 'j']))
for controller_data in data['Controllers']:
    for drive_data in controller_data['Response Data']['Drive Information']:
        if drive_data['State'] == 'DHS':
            print(drive_data)
