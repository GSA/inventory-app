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

# We need the public URL for the configuration file
APP_URL=$(echo $VCAP_APPLICATION | jq -r '.application_uris[0]')

# ... from which we can guess the service names

SVC_DATABASE="${APP_NAME}-db"
SVC_DATASTORE="${APP_NAME}-datastore"
SVC_S3="${APP_NAME}-s3"
SVC_REDIS="${APP_NAME}-redis"

# CKAN wants to know about two databases. We grab those URLs from the VCAP_SERVICES env var provided by the platform

DATABASE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATABASE $SVC_DATABASE '.["aws-rds"][] | select(.name == $SVC_DATABASE) | .credentials.uri')
DATASTORE_URL=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.uri')

# We need specific datastore URL components so we can construct another URL for the read-only user
DS_HOST=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.host')
DS_PORT=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.port')
DS_DBNAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_DATASTORE $SVC_DATASTORE '.["aws-rds"][] | select(.name == $SVC_DATASTORE) | .credentials.db_name')

# We need specific s3 variables so we can configure ckan to access s3
S3_REGION_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.region')
S3_BUCKET_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.bucket')
# S3_HOST_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.fips_endpoint')
# S3_PUBLIC_NAME=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.region')
S3_ACCESS_KEY_ID=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.access_key_id')
S3_SECRET_ACCESS_KEY=$(echo $VCAP_SERVICES | jq -r --arg SVC_S3 $SVC_S3 '.["s3"][] | select(.name == $SVC_S3) | .credentials.secret_access_key')

# We need the redis credentials for ckan to access redis, and we need to build the url
REDIS_HOST=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.["aws-elasticache-redis"][] | select(.name == $SVC_REDIS) | .credentials.host')
REDIS_PASSWORD=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.["aws-elasticache-redis"][] | select(.name == $SVC_REDIS) | .credentials.password')
REDIS_PORT=$(echo $VCAP_SERVICES | jq -r --arg SVC_REDIS $SVC_REDIS '.["aws-elasticache-redis"][] | select(.name == $SVC_REDIS) | .credentials.port')

# Edit the config file to use our values
ckan config-tool config/production.ini -s server:main -e port=${PORT}
ckan config-tool config/production.ini \
    "ckan.site_url=http://${APP_URL}" \
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

echo "Setting up the datastore user"
DATASTORE_URL=$DATASTORE_URL DS_RO_USER=$DS_RO_USER DS_RO_PASSWORD=$DS_RO_PASSWORD ./datastore-usersetup.py

# Run migrations
# paster --plugin=ckan db upgrade -c config/production.ini
ckan db upgrade -c config/production.ini 

# Fire it up!
exec ckan run -H 0.0.0.0 -p $PORT -c config/production.ini
# exec paster --plugin=ckan serve config/production.ini

