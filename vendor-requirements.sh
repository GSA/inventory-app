#!/bin/bash

set -o errexit
set -o pipefail

# This script installs some necessary .deb dependencies and then installs binary .whls for the packages
# specified in vendor-requirements.txt into the "vendor" directory. The actual process runs inside a Docker
# container; Docker is the only local prerequisite.

# Get the latest version of the cflinuxfs3 image
docker pull cloudfoundry/cflinuxfs3

# The bind mount here enables us to write back to the host filesystem
docker run --mount type=bind,source="$(pwd)",target=/home/vcap/app --name cf_bash --rm -i cloudfoundry/cflinuxfs3  /bin/bash -eu <<EOF

# Go where the app files are
cd ~vcap/app

# Install any packaged dependencies for our vendored packages
apt-get -y update
apt-get -y install swig build-essential python-dev libssl-dev

# Install PIP
curl https://bootstrap.pypa.io/2.7/get-pip.py -o /tmp/get-pip.py
python /tmp/get-pip.py

# As the VCAP user, cache .whls based on the frozen requirements for vendoring
mkdir -p src vendor
chown vcap.vcap vendor
chown vcap.vcap src
su - vcap -c 'cd app && pip download -r requirements.txt --no-binary=:none: -d vendor --exists-action=w'
EOF
