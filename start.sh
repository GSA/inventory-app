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
    --data-urlencode configSet=ckan2_5

  # Reload the core
  curl -v --get --fail --silent http://solr:8983/solr/admin/cores \
    --data-urlencode action=reload \
    --data-urlencode core=inventory
fi

# Work around for https://github.com/GSA/datagov-deploy/issues/961
# Use psycopg2==2.7.7 to do db init then switch back.
frozen_psycopg2=$(pip freeze | grep psycopg2)
pip install psycopg2==2.7.7
paster --plugin=ckan db init -c /etc/ckan/production.ini
pip install $frozen_psycopg2

# Run migrations
paster --plugin=ckan db upgrade -c /etc/ckan/production.ini

if [ "${1-}" = "seed" ]; then
  # Run seed script in new process
  echo running seed script...
  nohup /opt/inventory-app/seed.sh &> /tmp/nohup.out&
  # nohup some_command &> nohup2.out&
fi

# Work around https://github.com/GSA/catalog-app/issues/78
pip install -U repoze.who==2.0

echo starting ckan...
exec paster --plugin=ckan serve /etc/ckan/production.ini
