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
# Currently not installing properly, leaving out as not required
# pip3 install -r /app/requirements-dev.txt

# re-install ckan src directories (ckan extensions), that are not owned by root;
# these are mapped via docker volume and need to be installed in container
for i in $CKAN_HOME/src_extensions/*
do
  if [ -d $i ];
  then
    owner=$(stat -c '%U' $i);
    if [ $owner != 'root' ];
    then
      pip3 install -e $i
    fi
  fi
done

# Run migrations
ckan -c $CKAN_INI db upgrade 

# Run any startup scripts provided by images extending this one
if [[ -d "/docker-entrypoint.d" ]]
then
    for f in /docker-entrypoint.d/*; do
        case "$f" in
            *.sh)     echo "$0: Running init file $f"; . "$f" || true ;;
            *.py)     echo "$0: Running init file $f"; python3 "$f"; echo ;;
            *)        echo "$0: Ignoring $f (not an sh or py file)" ;;
        esac
        echo
    done
fi

echo starting xloader worker...
exec ckan -c $CKAN_INI  jobs worker & 

echo starting ckan...
sudo -u ckan -EH ckan -c $CKAN_INI run -H 0.0.0.0
# exec $CKAN_CONFIG/server_start.sh --paste $CKAN_INI -b 0.0.0.0:5000 -t 9000
