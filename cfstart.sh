#!/bin/bash

set -o errexit
set -o pipefail

# Utilize paster command, can remove when on ckan 2.9
function ckan () {
    paster --plugin=ckan "$@"
}
# set -o nounset # This option conflicts with the use of regex matching and $BASH_REMATCH

# At this point we expect that you've already setup these environment variables:
#   DS_RO_USER <datastore_username>
#   DS_RO_PASSWORD <datastore_password>
#   SOLR_URL <solr_url>

# We need to know the application name ...

APP_NAME=$(echo $VCAP_APPLICATION | jq -r '.application_name')
ORG_NAME=$(echo $VCAP_APPLICATION | jq -r '.organization_name')
SPACE_NAME=$(echo $VCAP_APPLICATION | jq -r '.space_name')

# We need the public URL for the configuration file
APP_URL=$(echo $VCAP_APPLICATION | jq -r '.application_uris[0]')

# ... from which we can guess the service names

SVC_DATABASE="${APP_NAME}-db"
SVC_DATASTORE="${APP_NAME}-datastore"
SVC_S3="${APP_NAME}-s3"
SVC_REDIS="${APP_NAME}-redis"
SVC_SECRETS="${APP_NAME}-secrets"

# CKAN wants to know about two databases. We grab those URLs from the VCAP_SERVICES env var provided by the platform

DATABASE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATABASE $SVC_DATABASE '.[][] | select(.name == $SVC_DATABASE) | .credentials.uri')
DATASTORE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.[][] | select(.name == $SVC_DATASTORE) | .credentials.uri')

# We need specific datastore URL components so we can construct another URL for the read-only user
DS_HOST=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.[][] | select(.name == $SVC_DATASTORE) | .credentials.host')
DS_PORT=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.[][] | select(.name == $SVC_DATASTORE) | .credentials.port')
DS_DBNAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.[][] | select(.name == $SVC_DATASTORE) | .credentials.db_name')

# We need specific s3 variables so we can configure ckan to access s3
S3_REGION_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.region')
S3_BUCKET_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.bucket')
# S3_HOST_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.fips_endpoint')
# S3_PUBLIC_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.region')
S3_ACCESS_KEY_ID=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.access_key_id')
S3_SECRET_ACCESS_KEY=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.[][] | select(.name == $SVC_S3) | .credentials.secret_access_key')

# We need the redis credentials for ckan to access redis, and we need to build the url
REDIS_HOST=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.[][] | select(.name == $SVC_REDIS) | .credentials.host')
REDIS_PASSWORD=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.[][] | select(.name == $SVC_REDIS) | .credentials.password')
REDIS_PORT=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.[][] | select(.name == $SVC_REDIS) | .credentials.port')

# We need the secret credentials for various application components (DB configuration, license keys, etc)
DS_RO_PASSWORD=$(echo $VCAP_SERVICES | jq -r --arg SVC_SECRETS $SVC_SECRETS '.[][] | select(.name == $SVC_SECRETS) | .credentials.DS_RO_PASSWORD')
export NEW_RELIC_LICENSE_KEY=$(echo $VCAP_SERVICES | jq -r --arg SVC_SECRETS $SVC_SECRETS '.[][] | select(.name == $SVC_SECRETS) | .credentials.NEW_RELIC_LICENSE_KEY')

# Edit the config file to use our values
export CKAN_INI=config/production.ini
ckan config-tool $CKAN_INI -s server:main -e port=${PORT}
ckan config-tool $CKAN_INI \
    "ckan.site_url=http://${APP_URL}" \
    "ckan.site_id=${ORG_NAME}-${SPACE_NAME}-${APP_NAME}" \
    "sqlalchemy.url=${DATABASE_URL}" \
    "solr_url=${SOLR_URL}" \
    "ckan.redis.url=rediss://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}" \
    "ckan.datastore.write_url=${DATASTORE_URL}" \
    "ckan.datastore.read_url=postgres://${DS_RO_USER}:${DS_RO_PASSWORD}@${DS_HOST}:${DS_PORT}/${DS_DBNAME}" \
    "ckanext.s3filestore.region_name=${S3_REGION_NAME}" \
    "ckanext.s3filestore.host_name=https://s3-${S3_REGION_NAME}.amazonaws.com" \
    "ckanext.s3filestore.aws_access_key_id=${S3_ACCESS_KEY_ID}" \
    "ckanext.s3filestore.aws_secret_access_key=${S3_SECRET_ACCESS_KEY}" \
    "ckanext.s3filestore.aws_bucket_name=${S3_BUCKET_NAME}" \
    "ckan.storage_path=/home/vcap/app/files"
    # "ckanext.s3filestore.public_host_name = http://localhost:4572"

ckan config-tool $CKAN_INI -s DEFAULT -e debug=false

echo "Setting up the datastore user"
DATASTORE_URL=$DATASTORE_URL DS_RO_USER=$DS_RO_USER DS_RO_PASSWORD=$DS_RO_PASSWORD ./datastore-usersetup.py

# Run migrations
# paster --plugin=ckan db upgrade -c config/production.ini
ckan db upgrade -c $CKAN_INI

# Fire it up!
exec config/server_start.sh -b 0.0.0.0:8080 -t 9000

