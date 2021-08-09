#!/usr/bin/env bats

# Log into application and save cookie for another application usage
function login () {
  curl --silent --fail 'http://app:5000/login_generic?came_from=/user/logged_in' --compressed -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: http://app:5000' -H 'Referer: http://app:5000/user/login' --data 'login=admin&password=password' --cookie-jar ./cookie-jar
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
