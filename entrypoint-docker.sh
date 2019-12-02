#!/bin/sh

. $CKAN_HOME/bin/activate

export PATH="$CKAN_HOME/bin:$PATH"

exec "$@"
