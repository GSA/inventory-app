#!/usr/bin/env bats

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

function clean_dataset {
  curl -X POST 'http://app:5000/api/3/action/package_delete' --cookie ./cookie-jar \
  -H 'content-type: application/json' \
  -d "{\"id\": \"$1\"}"
}

function add_datasets_for_draft_json {

  clean_dataset "draft-test-dataset-1"
  clean_dataset "draft-test-dataset-2"
  clean_dataset "test-dataset-3"

  # Add dataset 1 - draft
  data1="$(cat tests/draft_data_1.json)"
  curl -f -X POST 'http://app:5000/api/3/action/package_create' --cookie ./cookie-jar \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d "$data1"

  # Add dataset 2 - draft
  data1="$(cat tests/draft_data_2.json)"
  curl -f -X POST 'http://app:5000/api/3/action/package_create' --cookie ./cookie-jar \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d "$data1"

  # Add dataset 3 - not draft
  data1="$(cat tests/draft_data_3.json)"
  curl -f -X POST 'http://app:5000/api/3/action/package_create' --cookie ./cookie-jar \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d "$data1"
}

@test "Test Export draft.json working" {
  login
  add_datasets_for_draft_json

  # Get draft.json
  curl --fail --location --request GET --output draft.zip --cookie ./cookie-jar \
  'http://app:5000/organization/test-organization/draft.json'

  # Remove datasets to prevetn future conflicts
  clean_dataset "draft-test-dataset-1"
  clean_dataset "draft-test-dataset-2"
  clean_dataset "test-dataset-3"

  unzip -o draft.zip
  result=`cat draft_data.json | jq .dataset[].title`
  # We expect only dataset 1 and 2 to be draft-status
  expected='"Draft Test Dataset 1"
"Draft Test Dataset 2"'
  if [ "$result" = "$expected" ]; then
    echo "Success! Dataset 1 and 2 registered as draft"
    echo "Dataset 3 not registered as draft "
    return 0;
  else
    echo "$result does NOT equal $expected"
    return 1;
  fi

}
