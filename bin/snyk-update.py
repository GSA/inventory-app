
import json
import os

# Load results
scan_file = open('scan.json')
scan = json.load(scan_file)
scan_file.close()

# Make changes to fixable results
remediations = scan['remediation']['pin']
for k, v in remediations.items():
    package, old_version = k.split('@')
    new_version = v['upgradeTo'].split('@')[1]
    print(package, old_version, new_version)

    # Remove old version
    os.system('sed -i "/^%s\\(=\\|>\\|$\\)/Id" requirements.in.txt' % (package))

    # Add new version
    os.system("echo '%s' >> requirements.in.txt" %
              (package + ">=" + new_version))

# TODO: Handle unfixable results
