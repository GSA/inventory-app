#!/bin/bash

DIR="$(dirname "${BASH_SOURCE[0]}")"

# Run web application
# exec newrelic-admin run-program gunicorn -c "$DIR/gunicorn.conf.py" --worker-class gevent --paste $CKAN_INI "$@" --timeout 120 --workers 2

# start xloader
exec ckan jobs worker &
# Fire it up!
exec newrelic-admin run-program gunicorn "wsgi:application" --config "$DIR/gunicorn.conf.py" -b "0.0.0.0:$PORT" --chdir $DIR
