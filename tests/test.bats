#!/usr/bin/env bats

function wait_for () {
  # The app takes quite a while to startup (solr initialization and
  # migrations), close to a minute. Make sure to give it enough time before
  # starting the tests.

  local hostname=$1
  local port=$2
  local retries=20
  while ! nc -z -w 30 "$hostname" "$port" ; do
    if [ "$retries" -le 0 ]; then
      return 1
    fi

    retries=$(( $retries - 1 ))
    sleep 5
  done
}

# Log into application and save cookie for another application usage
function login () {
  curl --silent --fail 'http://app:5000/login_generic?came_from=/user/logged_in' --compressed -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://app:5000' -H 'Referer: http://app:5000/user/login' --data 'login=admin&password=password' --cookie-jar ./cookie-jar
}

function test_datastore_request () {
  #make a request to get cookies so that we can be logged on
  login
  package_id=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-1' --cookie ./cookie-jar | jq '.result | .id')

  datastore_request=$(curl --fail --location --request GET "http://app:5000/api/3/action/datastore_search?resource_id=_table_metadata" | grep -o '"success": true')
  if [ "$datastore_request" = '"success": true' ]; then
    #make a new package
    resource_id=$(curl -X POST 'http://app:5000/api/3/action/datastore_create' --cookie ./cookie-jar -d '{"resource": {"package_id": '$package_id'}, "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}' | jq '.result.resource_id')
    #delete resource
    delete_resource=$(curl -X POST 'http://app:5000/api/3/action/datastore_delete' --cookie ./cookie-jar -H "Authorization: $api_key" -d '{"resource_id": '$resource_id'}' | grep -o '"success": true')
    if [ "$delete_resource" = '"success": true' ]; then
      return 0;
    else
      return 1;
    fi
  else
    return 1
  fi
}


@test "app container is up" {
  wait_for app 5000
}

@test "/user/login is up" {
  curl --silent --fail http://app:5000/user/login
}

@test "private dataset accessible for user" {
  echo '3 Waiting 80 seconds to validate user & datasets have been seeded' >&3
  sleep 80
  login

  dataset_success=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-1' --cookie ./cookie-jar | jq -r '.success')

  [ "$dataset_success" = 'true' ]
}

@test "Add private dataset via API" {
  # Adding dataset(s) via API
  login
  curl -f -X POST 'http://app:5000/api/3/action/package_create' --cookie ./cookie-jar \
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
  "notes": "The description of the second test dataset",
  "owner_org": "test-organization",
  "bureau_code": "010:00",
  "contact_email": "tester@fake.com",
  "contact_name": "Tester",
  "modified": "2019-12-18",
  "public_access_level": "public",
  "publisher": "Department of the Interior",
  "unique_id": "doi-123456789",
  "title": "Test Dataset 2",
  "name": "test-dataset-2",
  "program_code": "010:001"
}'
}

@test "Add resource to existing private dataset via API" {
  # Adding resource(s) via API
echo -e "for,testing,purposes\n1,2,3" > test.csv
login
curl -f -X POST http://app:5000/api/action/resource_create  \
  --cookie ./cookie-jar \
  -F "package_id=test-dataset-2" \
  -F "name=test-resource-create" \
  -F "resource_type=CSV" \
  -F "format=CSV" \
  -F "upload=@test.csv"
}


@test "resource is accessible for the world" {
  # USmetadata hooks into edits to ensure datasets with resources are made public in order for the resource file to be publicly accessible.
  resource_id=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-2' | jq -r '.result.resources[0].id')
  package_id=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-2' | jq -r '.result.id')
  curl --fail --request GET "http://app:5000/dataset/$package_id/resource/$resource_id/download/test.csv"
}

@test "Remove dataset via API" {
  login
  curl -f -X POST http://app:5000/api/action/package_delete  \
  --cookie ./cookie-jar \
  -H 'content-type: application/json' \
  -d '
{
  "id": "test-dataset-2"
}'
}

@test "data is inaccessible to public" {
  [ "404" == "$(curl --silent --output /dev/null --write-out %{http_code} http://app:5000/dataset/test-dataset-1)" ]
  [ "403" == "$(curl --silent --output /dev/null --write-out %{http_code} http://app:5000/api/action/package_show?id=test-dataset-1)" ]
}

@test "Website display is working" {
  login
  curl --silent --fail http://app:5000/dataset/test-dataset-1 --cookie ./cookie-jar
}

@test "/dataset is inaccessible to public" {
  run curl --fail http://app:5000/dataset
  # Validate output is 22, curl response for 403 (Forbidden)
  [ "$status" -eq 22 ]
}

@test "Google Analytics ID present" {
  login
  google_id='google-analytics-fake-key-testing-87654321' #this is completely random. Set to "googleanalytics.ids" in production.ini file
  find_id=$(curl --silent --fail --request GET 'http://app:5000/dataset' --cookie ./cookie-jar | grep -o "$google_id")

  if  [ "$find_id" = "$google_id" ]; then
    return 0;
  else
    return 1;
  fi
}

@test "Datastore functioning properly" {
  test_datastore_request
}

@test "usmetadata working" {
  login
  common_core=$(curl -X GET "http://app:5000/dataset/test-dataset-1" --cookie ./cookie-jar | grep -o "Common Core Metadata")
  if [ "$common_core" = "Common Core Metadata" ]; then
    return 0;
  else
    return 1;
  fi
}

@test "datapusher working" {
  curl --silent --fail "http://datapusher:8000/status" | grep push_to_datastore
}

@test "datapusher API working" {
  login
  resource_id=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-1' --cookie ./cookie-jar | jq -r '.result.resources[0].id')
  curl --fail --location --request GET "http://app:5000/api/3/action/datastore_search?resource_id=$resource_id&limit=5" --cookie ./cookie-jar
}
