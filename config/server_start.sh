#!/bin/bash

# DIR="$(dirname "${BASH_SOURCE[0]}")"

# Run web application
# exec newrelic-admin run-program gunicorn -c "$DIR/gunicorn.conf.py" --worker-class gevent --paste $CKAN_INI "$@" --timeout 120 --workers 2

# start xloader
exec ckan jobs worker &
# Fire it up!
exec ckan run --host "0.0.0.0" --port $PORT
# exec config/server_start.sh -b 0.0.0.0:$PORT -t 9000
