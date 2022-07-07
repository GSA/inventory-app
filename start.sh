#!/bin/bash

set -e

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
    if [ -f $i/setup.py ];
    then
        cd $i
        echo "Found setup.py file in $i"
        # Uninstall any current implementation of the code
        echo uninstalling "${PWD##*/}"
        pip3 uninstall -y "${PWD##*/}"
        # Install the extension in editable mode
        pip3 install -e .
        cd $APP_DIR
    fi
  fi
done

pip3 install -e /app/.

# Set debug to true
echo "Enabling debug mode"
ckan config-tool $CKAN_INI -s DEFAULT "debug = true"

# Run migrations
ckan db upgrade

# Add ckan core to solr
# /app/solr/migrate-solrcloud-schema.sh $COLLECTION_NAME

# Run the prerun script to init CKAN and create the default admin user
python3 ${CKAN_HOME}/GSA_prerun.py


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
exec ckan jobs worker & 

echo starting ckan...
# sudo -u ckan -EH ckan -c $CKAN_INI run -H 0.0.0.0
exec $CKAN_CONFIG/server_start.sh
