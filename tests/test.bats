#!/usr/bin/env bats

function wait_for () {
  # The app takes quite a while to startup (solr initialization and
  # migrations), close to a minute. Make sure to give it enough time before
  # starting the tests.

  local hostname=$1
  local port=$2
  local retries=10
  while ! nc -z -w 30 "$hostname" "$port" ; do
    if [ "$retries" -le 0 ]; then
      return 1
    fi

    retries=$(( $retries - 1 ))
    sleep 5
  done
}

function test_login_and_datasets () {
  sleep 15 # Validate that the seed file has time to implement
  curl --silent --fail 'http://app:5000/login_generic?came_from=/user/logged_in' --compressed -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://app:5000' -H 'Referer: http://app:5000/user/login' --data 'login=admin&password=password' --cookie-jar ./cookie-jar

  dataset_success=$(curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-1' --cookie ./cookie-jar | grep -o '"success": true')

  if [ "$dataset_success" = '"success": true' ]; then
    return 0;
  else
    return 1;
  fi
}

#checks that the google id is in the html response
function check_google_id () {
  google_id='google-analytics-fake-key-testing-87654321' #this is completely random. Set to "googleanalytics.ids" in production.ini file
  find_id=$(curl --silent --fail --request GET 'http://app:5000' | grep -o "$google_id")

  if  [ "$find_id" = "$google_id" ]; then
    return 0;
  else
    return 1;
  fi
}

function test_datastore_request () {
  #make a request to get cookies so that we can be logged on
  curl --silent --fail 'http://app:5000/login_generic?came_from=/user/logged_in' --compressed -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://app:5000' -H 'Referer: http://app:5000/user/login' --data 'login=admin&password=password' --cookie-jar ./cookie-jar
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

@test "data is accessible for user" {
  test_login_and_datasets
}

@test "data is inaccessible to public" {
  run curl --fail --location --request GET 'http://app:5000/api/3/action/package_show?id=test-dataset-1'
  # Validate output is 22, curl response for 403 (Forbidden)
  [ "$status" -eq 22 ]
}

@test "Website display is working" {
  curl --silent --fail http://app:5000/dataset/test-dataset-1 --cookie ./cookie-jar
}

@test "Google Analytics ID present" {
  check_google_id
}

@test "Datastore functioning properly" {
  test_datastore_request
}

@test "usmetadata working" {
  curl 'http://app:5000/login_generic?came_from=/user/logged_in' --compressed -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://app:5000' -H 'Referer: http://app:5000/user/login' --data 'login=admin&password=password' --cookie-jar ./cookie-jar
  common_core=$(curl -X GET "http://app:5000/dataset/test-dataset-1" --cookie ./cookie-jar | grep -o "Common Core Metadata")
  if [ "$common_core" = "Common Core Metadata" ]; then
    return 0;
  else
    return 1;
  fi
}

@test "datapusher working" {
  datapusher_status=$(curl -X GET "http://datapusher:8000/status" | grep -o "push_to_datastore")
  # {"job_types": ["push_to_datastore"], "name": "datapusher", "stats": {"complete": 0, "error": 0, "pending": 0}, "version": 0.1}
  if [ "$datapusher_status" = "push_to_datastore" ]; then
    return 0;
  else
    return 1;
  fi
}