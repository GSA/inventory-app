#!/bin/bash

set -o errexit
set -o pipefail

# Add the current directory to our virtualenv
pip3 install -e .

function vcap_get_service () {
  local path name
  name="$1"
  path="$2"
  service_name=${APP_NAME}-${name}
  echo $VCAP_SERVICES | jq --raw-output --arg service_name "$service_name" ".[][] | select(.name == \$service_name) | $path"
}

# Create a staging area for secrets and files
CONFIG_DIR=$(mktemp -d)
SHARED_DIR=$(mktemp -d)

# We need to know the application name ...
APP_NAME=$(echo $VCAP_APPLICATION | jq -r '.application_name')
APP_URL=$(echo $VCAP_APPLICATION | jq -r '.application_uris[0]')

# We need specific datastore URL components so we can construct another URL for the read-only user
DS_HOST=$(vcap_get_service datastore .credentials.host)
DS_PORT=$(vcap_get_service datastore .credentials.port)
DS_DBNAME=$(vcap_get_service datastore .credentials.db_name)

# We need the redis credentials for ckan to access redis, and we need to build the url to use the rediss
REDIS_HOST=$(vcap_get_service redis .credentials.host)
REDIS_PASSWORD=$(vcap_get_service redis .credentials.password)
REDIS_PORT=$(vcap_get_service redis .credentials.port)

SAML2_PRIVATE_KEY=$(vcap_get_service secrets .credentials.SAML2_PRIVATE_KEY)

export CKANEXT__SAML2AUTH__KEY_FILE_PATH=${CONFIG_DIR}/saml2_key.pem
export CKANEXT__SAML2AUTH__CERT_FILE_PATH=${CONFIG_DIR}/saml2_certificate.pem

# We need the secret credentials for various application components (DB configuration, license keys, etc)
DS_RO_PASSWORD=$(vcap_get_service secrets .credentials.DS_RO_PASSWORD)
export NEW_RELIC_LICENSE_KEY=$(vcap_get_service secrets .credentials.NEW_RELIC_LICENSE_KEY)
export CKAN___BEAKER__SESSION__SECRET=$(vcap_get_service secrets .credentials.CKAN___BEAKER__SESSION__SECRET)
export CKAN___CACHE_DIR=${SHARED_DIR}/cache

# Get sysadmins list by a user-provided-service per environment
export CKANEXT__SAML2AUTH__SYSADMINS_LIST=$(echo $VCAP_SERVICES | jq --raw-output ".[][] | select(.name == \"sysadmin-users\") | .credentials.CKANEXT__SAML2AUTH__SYSADMINS_LIST")

# ckan reads some environment variables... https://docs.ckan.org/en/2.9/maintaining/configuration.html#environment-variables
export CKAN_SQLALCHEMY_URL=$(vcap_get_service db .credentials.uri)
export CKAN___BEAKER__SESSION__URL=${CKAN_SQLALCHEMY_URL}
export CKAN_DATASTORE_WRITE_URL=$(vcap_get_service datastore .credentials.uri)
export CKAN_DATASTORE_READ_URL=postgres://$DS_RO_USER:$DS_RO_PASSWORD@$DS_HOST:$DS_PORT/$DS_DBNAME
export CKAN_REDIS_URL=rediss://:$REDIS_PASSWORD@$REDIS_HOST:$REDIS_PORT
export CKAN_STORAGE_PATH=${SHARED_DIR}/files
export CKAN_SOLR_BASE_URL=https://$(vcap_get_service solr .credentials.domain)
export CKAN_SOLR_USER=$(vcap_get_service solr .credentials.username)
export CKAN_SOLR_PASSWORD=$(vcap_get_service solr .credentials.password)

# Use ckanext-envvars to import other configurations...
export CKANEXT__S3FILESTORE__REGION_NAME=$(vcap_get_service s3 .credentials.region)
export CKANEXT__S3FILESTORE__HOST_NAME=https://s3-$CKANEXT__S3FILESTORE__REGION_NAME.amazonaws.com
export CKANEXT__S3FILESTORE__AWS_ACCESS_KEY_ID=$(vcap_get_service s3 .credentials.access_key_id)
export CKANEXT__S3FILESTORE__AWS_SECRET_ACCESS_KEY=$(vcap_get_service s3 .credentials.secret_access_key)
export CKANEXT__S3FILESTORE__AWS_BUCKET_NAME=$(vcap_get_service s3 .credentials.bucket)
export CKANEXT__S3FILESTORE__AWS_STORAGE_PATH=datagov/inventory-next
# xloader uses the same db as datastore
export CKANEXT__XLOADER__JOBS_DB__URI=$(vcap_get_service datastore .credentials.uri)

# Write out any files and directories
mkdir -p $CKAN_STORAGE_PATH
mkdir -p $CKAN___CACHE_DIR
echo "$SAML2_PRIVATE_KEY" | base64 -d > $CKANEXT__SAML2AUTH__KEY_FILE_PATH
echo "$SAML2_CERTIFICATE" > $CKANEXT__SAML2AUTH__CERT_FILE_PATH
# Update local path with full path
export CKANEXT__SAML2AUTH__IDP_METADATA__LOCAL_PATH="${HOME}/${CKANEXT__SAML2AUTH__IDP_METADATA__LOCAL_PATH}"

# Set up the collection in Solr
echo Setting up Solr collection
export SOLR_COLLECTION=ckan
# ./solr/migrate-solrcloud-schema.sh $SOLR_COLLECTION
export CKAN_SOLR_URL=$CKAN_SOLR_BASE_URL/solr/$SOLR_COLLECTION

# Edit the config file to validate debug is off and utilizes the correct port
export CKAN_INI="${HOME}/config/ckan.ini"
# ckan config-tool $CKAN_INI -s server:main -e port=${PORT}
ckan config-tool $CKAN_INI --section DEFAULT --edit debug=false

echo "Setting up the datastore user"
DATASTORE_URL=$CKAN_DATASTORE_WRITE_URL DS_RO_USER=$DS_RO_USER DS_RO_PASSWORD=$DS_RO_PASSWORD python3 datastore-usersetup.py

# Run migrations
# paster --plugin=ckan db upgrade -c config/ckan.ini
ckan -c $CKAN_INI db upgrade
