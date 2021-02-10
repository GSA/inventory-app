#!/bin/bash

set -o errexit
set -o pipefail

# Install any packaged dependencies for our vendored packages
apt-get -y update
apt-get -y install swig build-essential python-dev libssl-dev

pip wheel -w vendor -r requirements.txt
