#!/bin/bash

# Can optionally specify an api key if the user is already created. Add as second argument to command.

set -o errexit
set -o pipefail
set -o nounset

if [ "${1-}" == "" ]; then
  #Setup various users, organizations, and datasets
  /usr/lib/ckan/bin/paster --plugin=ckan user add admin password=admin email=fake@fake.com -c /etc/ckan/production.ini > /tmp/user_temp.txt
  /usr/lib/ckan/bin/paster --plugin=ckan sysadmin add admin -c /etc/ckan/production.ini
  api_key=$(grep -oP "apikey.: u.\K.+" /tmp/user_temp.txt | cut -d "'" -f1)

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
  "creator_user_id": "5c1231ea-9d6c-4db1-95ab-175a4c11d764",
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
      "package_id": "c9842276-77d7-4082-8e20-d53d04ba3211",
      "webstore_last_updated": null,
      "datastore_active": false,
      "id": "e61acaac-c7b7-4be6-a7fd-033a3c0509e0",
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
      "revision_id": "02c5540a-ec1a-4ae1-afd7-1b3c57d8d9b5",
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
