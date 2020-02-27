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
