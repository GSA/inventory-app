#!/bin/bash

set -o errexit
set -o pipefail

# Install any packaged dependencies for our vendored packages
sudo apt-get -y update
sudo apt-get -y install swig build-essential python-dev libssl-dev

pip wheel -w vendor -r requirements.txt
