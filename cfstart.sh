#!/bin/bash

set -o errexit
set -o pipefail
# set -o nounset # This option conflicts with the use of regex matching and $BASH_REMATCH

# At this point we expect that you've already done:
#   cf set-env <appname> DS_RO_USER <datastore_username>
#   cf set-env <appname> DS_RO_PASSWORD <datastore_password>
#   cf set-env <appname> SOLR_URL <solr_url>

# We need to know the application name ...

APP_NAME=$(echo $VCAP_APPLICATION | jq -r '.application_name')

# ... from which we can guess the service names

SVC_DATABASE="${APP_NAME}-db"
SVC_DATASTORE="${APP_NAME}-datastore"

# CKAN wants to know about two databases. We grab those URLs from the VCAP_SERVICES env var provided by the platform

DATABASE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATABASE $SVC_DATABASE '.["aws-rds"][] | select(.name == $SVC_DATABASE) | .credentials.uri')
DATASTORE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.uri')

# We need specific datastore URL components so we can construct another URL for the read-only user
DS_HOST=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.host')
DS_PORT=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.port')
DS_DBNAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.db_name')

# Edit the config file to use our values
paster --plugin=ckan config-tool config/production.ini -s server:main -e port=${PORT}
paster --plugin=ckan config-tool config/production.ini \
    "sqlalchemy.url=${DATABASE_URL}" \
    "solr_url=${SOLR_URL}" \
    "ckan.datastore.write_url=${DATASTORE_URL}" \
    "ckan.datastore.read_url=postgres://${DS_RO_USER}:${DS_RO_PASSWORD}@${DS_HOST}:${DS_PORT}/${DS_DBNAME}"

echo "Setting up the datastore user"
DATASTORE_URL=$DATASTORE_URL DS_RO_USER=$DS_RO_USER DS_RO_PASSWORD=$DS_RO_PASSWORD ./datastore-usersetup.py

# Run migrations
paster --plugin=ckan db upgrade -c config/production.ini

# TODO: This only applies for development; in staging and production SAML should be configured!
# In order to work around https://github.com/GSA/catalog-app/issues/78 we need PIP to make a package change
curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
python /tmp/get-pip.py
pip install -U repoze.who==2.0

# Fire it up!
exec paster --plugin=ckan serve config/production.ini

