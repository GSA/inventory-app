#!/bin/bash

set -o errexit
set -o pipefail

venv=$(mktemp -d)

function cleanup () {
  rm -rf $venv
}

trap cleanup EXIT

virtualenv $venv -p /usr/local/bin/python
${venv}/bin/pip install -r requirements.in.txt

${venv}/bin/pip freeze --quiet > requirements.txt
