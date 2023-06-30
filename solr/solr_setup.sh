#!/bin/bash

mkdir -p /tmp/ckan_config

# Remove any restored EFS backups
rm -rf /var/solr/data/aws-backup-restore*
# TODO: replace existing (bad) core with the correct (good) restore directory


# In case of ECS Task stop and start, we need to make sure the Solr Core on EFS is not locked for new Task to use it.
# We use SOLR simple locktype. This code block gives old Task up to 5 mins to clear the lock file on EFS before exit.
# If it's been more than 5 mins, it means the old Task crashes without clearing the lock. Then the lockfile is force deleted.
export lockpath="/var/solr/data/ckan/data/index*"
export flagfile="/var/solr/data/retry-flag";
[[ $(find $lockpath -name write.lock) && ! -f $flagfile ]] && { echo "Found lock file. Creating flag file."; touch $flagfile; sleep 10; };
[[ $(find $lockpath -name write.lock) && ! $(find $flagfile -mmin +5) ]] && { echo "Keep waiting."; exit 1; };
ls -lart /var/solr/data;
ls -lart /var/solr/data/ckan/data;
find $lockpath -name write.lock -delete;
rm -rf $flagfile;

# add solr config files for ckan 2.9
wget -O /tmp/ckan_config/schema.xml https://raw.githubusercontent.com/GSA/inventory-app/main/solr/schema.xml
wget -O /tmp/ckan_config/protwords.txt https://raw.githubusercontent.com/GSA/inventory-app/main/solr/protwords.txt
wget -O /tmp/ckan_config/solrconfig.xml https://raw.githubusercontent.com/GSA/inventory-app/main/solr/solrconfig.xml
wget -O /tmp/ckan_config/stopwords.txt https://raw.githubusercontent.com/GSA/inventory-app/main/solr/stopwords.txt
wget -O /tmp/ckan_config/synonyms.txt https://raw.githubusercontent.com/GSA/inventory-app/main/solr/synonyms.txt

# Check if users already exist
SECURITY_FILE=/var/solr/data/security.json
if [ -f "$SECURITY_FILE" ]; then
  echo "Solr ckan and authentication are set up already :)"
  exit 0;
fi

# add solr authentication
cat <<SOLRAUTH > $SECURITY_FILE
{
"authentication":{
   "blockUnknown": true,
   "class":"solr.BasicAuthPlugin",
   "credentials":{"catalog":"rJzrn+HooKn79Q+cfysdGKmMhJbtj0Q1bTokFud6f9o= eKuBUjAoBIkJAMYZxJU6HOKSchTAce+DoQrY5Vewu7I="},
   "realm":"data.gov users",
   "forwardCredentials": false
},
"authorization":{
   "class":"solr.RuleBasedAuthorizationPlugin",
   "permissions":[{"name":"security-edit",
      "role":"admin"}],
   "user-role":{"catalog":"admin"}
}}
SOLRAUTH

#  group user solr:solr is 8983:8983 in solr docker image
chown -R 8983:8983 /var/solr/data/
