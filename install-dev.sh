#!/bin/bash
#
# Initializes the development environment by installing the app dependencies.
# We assume you already have your virtualenv activated.

if [[ -z "$VIRTUAL_ENV" ]]; then
  echo You must activate your python virutal environment first. >&2
  exit 1
fi

set -o errexit
set -o pipefail
set -o nounset

pip install -r requirements.txt

# Install development dependencies of extensions
# TODO extensions should declare runtime dependencies in setup.py
EXTENSIONS=$(cat requirements.txt | grep -o "egg=.*" | cut -f2- -d'=')

# install/setup each extension individually
for extension in $EXTENSIONS; do
    if [ -f $VIRTUAL_ENV/src/$extension/requirements.txt ]; then
        $VIRTUAL_ENV/bin/pip install -r $VIRTUAL_ENV/src/$extension/requirements.txt
    elif [ -f $VIRTUAL_ENV/src/$extension/pip-requirements.txt ]; then
        $VIRTUAL_ENV/bin/pip install -r $VIRTUAL_ENV/src/$extension/pip-requirements.txt
    fi
done

