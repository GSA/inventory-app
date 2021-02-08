#!/bin/bash

DIR="$(dirname "${BASH_SOURCE[0]}")"

# Run web application
exec newrelic-admin run-program gunicorn --worker-class gevent --paste $CKAN_INI "$@"
