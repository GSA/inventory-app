# Setup the cypress user in CKAN for testing
ckan -c $CKAN_INI user add cypress-user password=cypress-user-password email=test@gsa.gov
ckan -c $CKAN_INI sysadmin add cypress-user