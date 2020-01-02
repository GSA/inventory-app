#!/usr/bin/env bats

function wait_for () {
  # The app takes quite a while to startup (solr initialization and
  # migrations), close to a minute. Make sure to give it enough time before
  # starting the tests.
  local retries=10
  while ! nc -z -w 30 app 80; do
    if [ "$retries" -le 0 ]; then
      return 1
    fi

    retries=$(( $retries - 1 ))
    sleep 5
  done
}

@test "app container is up" {
  run wait_for app 5000
}

@test "/user/login is up" {
  run curl --silent --fail http://app:5000/user/login
  [ $status -eq 0 ]
}
