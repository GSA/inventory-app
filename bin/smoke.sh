#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

# TODO move smoke tests to python

curl --fail --silent ${APP_URL}/api/action/status_show?$(date +%s) > /dev/null
[ "403" == "$(curl --silent --output /dev/null --write-out %{http_code} ${APP_URL}/dataset?$(date +%s))" ]

echo ok
