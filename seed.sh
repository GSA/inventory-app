#!/bin/bash

# Can optionally specify an api key if the user is already created. Add as second argument to command.

set -o errexit
set -o pipefail
set -o nounset

# The app takes quite a while to startup (solr initialization and
# migrations), close to a minute. Make sure to give it enough time before
# starting the tests.

hostname="localhost"
port="5000"
retries=20
while ! nc -z -w 30 "$hostname" "$port" ; do
  if [ "$retries" -le 0 ]; then
    return 1
  fi

  retries=$(( $retries - 1 ))
  echo 'retrying...'
  sleep 5
done

#If api_key is passed, utilize; if not, create new user
if [ "${1-}" == "" ]; then
  echo creating user admin
  #Setup various users, organizations, and datasets
  if /usr/lib/ckan/bin/paster --plugin=ckan user add admin password=password email=fake@fake.com -c $CKAN_INI > /tmp/user_temp.txt ; then
    /usr/lib/ckan/bin/paster --plugin=ckan sysadmin add admin -c $CKAN_INI
    api_key=$(grep -oP "apikey.: u.\K.+" /tmp/user_temp.txt | cut -d "'" -f1)
  else
    api_key=$(/usr/lib/ckan/bin/paster --plugin=ckan user admin -c $CKAN_INI | grep -oP "apikey=\K.+ " | cut -d " " -f1)
  fi

else
  api_key="$1"
fi

# Adding organization
curl -X POST \
  http://localhost:5000/api/3/action/organization_create \
  -H "authorization: $api_key" \
  -H "cache-control: no-cache" \
  -d '{"description": "Test organization","title": "Test Organization","approval_status": "approved","state": "active","name": "test-organization"}'

echo ''

# Make sure package is removed
curl -X POST http://app:5000/api/action/package_delete  \
  -H "authorization: $api_key" \
  -H 'content-type: application/json' \
  -d '
{
  "id": "test-dataset-1"
}'

# Adding dataset(s) via API
curl -X POST \
  http://localhost:5000/api/3/action/package_create \
  -H "authorization: $api_key" \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '
{
  "license_title": "License not specified",
  "maintainer": null,
  "relationships_as_object": [],
  "private": true,
  "maintainer_email": null,
  "num_tags": 1,
  "metadata_created": "2019-12-18T19:01:33.429530",
  "metadata_modified": "2019-12-18T19:02:54.841495",
  "author": null,
  "author_email": null,
  "state": "active",
  "version": null,
  "type": "dataset",
  "resources": [
    {
      "conformsTo": "",
      "cache_last_updated": null,
      "describedByType": "",
      "labels": {
        "accessURL new": "Access URL",
        "conformsTo": "Conforms To",
        "describedBy": "Described By",
        "describedByType": "Described By Type",
        "format": "Media Type",
        "formatReadable": "Format",
        "created": "Created"
      },
      "webstore_last_updated": null,
      "clear_upload": "",
      "state": "active",
      "size": null,
      "describedBy": "",
      "hash": "",
      "description": "",
      "format": "CSV",
      "mimetype_inner": null,
      "url_type": null,
      "formatReadable": "",
      "mimetype": null,
      "cache_url": null,
      "name": "Test Resource",
      "created": "2019-12-18T19:02:54.448285",
      "url": "https://www.bia.gov/tribal-leaders-csv",
      "upload": "",
      "webstore_url": null,
      "last_modified": null,
      "position": 0,
      "resource_type": "file"
    }
  ],
  "num_resources": 1,
  "tags": [
    {
      "vocabulary_id": null,
      "state": "active",
      "display_name": "test",
      "id": "65c76784-e271-4eb1-9778-a738622a1a3d",
      "name": "test"
    }
  ],
  "tag_string": "test",
  "groups": [],
  "license_id": "notspecified",
  "relationships_as_subject": [],
  "organization": "test-organization",
  "isopen": false,
  "url": null,
  "notes": "The description of the test dataset",
  "owner_org": "test-organization",
  "bureau_code": "010:00",
  "contact_email": "tester@fake.com",
  "contact_name": "Tester",
  "modified": "2019-12-18",
  "public_access_level": "public",
  "publisher": "Department of the Interior",
  "unique_id": "doi-123456789",
  "title": "Test Dataset 1",
  "name": "test-dataset-1",
  "program_code": "010:001"
}'