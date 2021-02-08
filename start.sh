#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

function wait_for () {
  local host=$1
  local port=$2

  while ! nc -z -w 5 "$host" "$port"; do
    sleep 1
  done
}

wait_for solr 8983
wait_for db 5432
wait_for localstack-container 4572

# Even though solr is listening, it needs a moment before the core status
# check will return successfully.
sleep 1

# Check if the solr core exists.
if ! (curl --get --fail --silent http://solr:8983/solr/admin/cores \
  --data-urlencode action=status \
  --data-urlencode core=inventory | grep -q segmentsFileSizeInBytes); then

  # Create the solr core
  curl -v --get --fail --silent http://solr:8983/solr/admin/cores \
    --data-urlencode action=create \
    --data-urlencode name=inventory \
    --data-urlencode configSet=ckan2_8

  # Reload the core
  curl -v --get --fail --silent http://solr:8983/solr/admin/cores \
    --data-urlencode action=reload \
    --data-urlencode core=inventory
fi

# Install dev dependencies after build so freezing dependencies
# works as expected.
$CKAN_HOME/bin/pip install -r /opt/inventory-app/requirements-dev.txt

# re-install ckan src directories (ckan extensions), that are not owned by root;
# these are mapped via docker volume and need to be installed in container
for i in $CKAN_HOME/src/*
do
  if [ -d $i ];
  then
    owner=$(stat -c '%U' $i);
    if [ $owner != 'root' ];
    then
      $CKAN_HOME/bin/pip install -e $i
    fi
  fi
done

# Run migrations
paster --plugin=ckan db upgrade -c $CKAN_INI

if [ "${1-}" = "seed" ]; then
  # Run seed script in new process
  echo running seed script...
  nohup /opt/inventory-app/seed.sh &> /tmp/nohup.out&
  # nohup some_command &> nohup2.out&
fi

echo starting ckan...
exec $CKAN_CONFIG/server_start.sh --paste $CKAN_INI -b 0.0.0.0:5000 -t 9000
