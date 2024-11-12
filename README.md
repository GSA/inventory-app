# inventory-app

[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).  For details on the system architecture, please see our [data.gov systems list](https://github.com/GSA/data.gov/blob/master/SYSTEMS.md)!

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies. Very little works beyond that._

## Development
 
### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)
- [Cloud Foundry](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html) CLI v7

### Getting started

Build and bring up the containers.

    make up
    make up-with-data [_Gives development environment basic user, organization, and dataset_]

Open CKAN to verify it's working

    open http://localhost:5000

If you would like to seed data into the system, examine the test framework (`e2e/cypress/support/command.js`) for some examples of creating organizations and/or datasets with resources.

### docker compose commands

To enter into the app container in interactive mode as root, you will need to run the following:

    docker compose exec app /bin/bash

To run a one off command inside the container:

    docker compose exec app {command}

### Update dependencies

Update the "lock" file for dependencies.

    make build requirements

This freezes the requirements at `requirements.txt`. Run the tests with the
updated dependencies.

    make test

### Live Editing

To edit CKAN or extension code live, the local code needs to be attached via a volume.
Add a local extension folder path into the `docker-compose.yml` file that you would like to edit
(see volume section for commented example).
After editing the extension/ckan core (see below), run `make up` (the app will not start appropriately)
then run `make debug` to restart the application with an interactive console.

_TODO: tested `--reload` functionality of gunicorn, but [does not work well with paster flag](https://docs.gunicorn.org/en/stable/settings.html#reload)._
_Hopefully this option improves in the future._

#### Debugger

Add `import ipdb; ipdb.set_trace()` as a new line where you would like to start debugging. Then run `make debug`, and a new instance of the ckan app will be started that has an interactive console. Once the debugger statement is triggered, then a command prompt should display in the console. See [documentation](https://docs.python.org/3/library/pdb.html#debugger-commands) for available commands. `ipdb` is preferred for styling/readability reasons, but `pdb` will work as well. `web-pdb` was tested, but has various timing complications of it's own that causes unnecessary complications and failures.

The flask debugger is also imported as a dev requirement and turned on by default in the
`development.ini` file (`debug = true`), which gives some UI tools on the webpage to parse stack
traces and various other examination tools. The behavior is inconsistent, probably due to
ckan serving pages as pylons sometimes and flask at others.

**Make sure you remove all pdb statements before commiting to any repository!**

### Tests

    make test

The tests utilize cypress. The above command runs in "headless" mode, and debugging capabilities are limited. To fully install and rapidly iterate on tests, install cypress locally with npm.

    npm install cypress

Then, you should be able to run `make cypress` to turn on cypress in interactive mode. If you are using WSL you may need additional setup. Start at [this walkthrough](https://nickymeuleman.netlify.app/blog/gui-on-wsl2-cypress), and consider asking a team member for setup help. You will also need to install npx to use the make command.

Please be aware that the tests attempt to clean themselves after each spec file by specifically removing datasets and organizations. If datasets are manually added into the test organization, the dataset and organization may not be removed and this may have unintended consequences. If the system is in a bad state, you should be able to run `make clean` to restart in a clean environment.

#### Extension Tests

_TODO: add details about running and editing extension tests here._

## Deploying to cloud.gov

Copy `vars.yml.template` to `vars.yml`, and customize the values in that file. Then, assuming you're logged in for the Cloud Foundry CLI:

Create the database used by datastore. `${app_name}` should be the same as what you have in vars.yml.

    cf create-service aws-rds micro-psql ${app_name}-datastore --wait

Create the database used by CKAN itself. You have to wait a bit for the datastore DB to be available.

    cf create-service aws-rds small-psql ${app_name}-db --wait

Create the s3 bucket for data storage.

    cf create-service s3 basic-sandbox ${app_name}-s3 --wait

Create the Redis service for cache

    cf create-service aws-elasticache-redis redis-dev ${app_name}-redis --wait

Deploy the Solr instance.

    cf push --vars-file vars.yml ${app_name}-solr --wait

Create the secrets service to store secret environment variables. See [Secrets](#secrets) below.

Deploy the CKAN app.

    cf push --vars-file vars.yml ${app_name}

Ensure the inventory app can reach the Solr app.

    cf add-network-policy ${app_name} ${app_name}-solr --protocol tcp --port 8983

You should now be able to visit `https://[ROUTE]`, where `[ROUTE]` is the route reported by `cf app ${app_name}`.

### Secrets

Tips on managing
[secrets](https://github.com/GSA/datagov-deploy/wiki/Cloud.gov-Cheat-Sheet#secrets-management).
When creating the service for the first time, use `create-user-provided-service`
instead of update.

    cf update-user-provided-service ${app_name}-secrets -p "CKAN___BEAKER__SESSION__SECRET, CKAN___WTF_CSRF_SECRET_KEY, DS_RO_PASSWORD, NEW_RELIC_LICENSE_KEY, SAML2_PRIVATE_KEY"

Name | Description | Where to find
---- | ----------- | -------------
CKAN___BEAKER__SESSION__SECRET | Session secret for encrypting CKAN sessions.  | `pwgen -s 32 1`
CKAN___WTF_CSRF_SECRET_KEY | CSRF secret for generating CSRF tokens.  | `pwgen -s 32 1`
DS_RO_PASSWORD | Read-only password to configure for the [datastore](https://docs.ckan.org/en/2.9/maintaining/datastore.html) user. | Initially randomly generated [#2839](https://github.com/GSA/datagov-deploy/issues/2839)
NEW_RELIC_LICENSE_KEY | New Relic License key. | New Relic account settings.
SAML2_PRIVATE_KEY | Base64 encoded SAML2 key matching the certificate configured for Login.gov | [Google Drive](https://drive.google.com/drive/u/0/folders/1VguFPRiRb1Ljnm_6UShryHWDofX0xBnU).

### CI configuration

Create a GitHub environment for each application you're deploying. Each
GH environment should be configured with secrets from a [ci-deployer service
account](https://github.com/GSA/datagov-deploy/wiki/Cloud.gov-Cheat-Sheet#space-organization).

Secret name | Description
----------- | -----------
CF_SERVICE_AUTH | The service key password.
CF_SERVICE_USER | The service key username.

## Login.gov integration

We use Login.gov as our
[SAML2](https://github.com/GSA/datagov-deploy/wiki/SAML2-authentication)
Identity Provider (IdP). Production apps use the production Login.gov instance
while other apps use the Login.gov identity sandbox.

Each year in March, Login.gov rotates their credentials. See our
[wiki](https://github.com/GSA/datagov-deploy/wiki/SAML2-authentication#working-with-logingov)
for details.

Our Service Provider (SP) certificate and key are provided in through
environment variable and user-provided service.

The Login.gov IdP metadata is stored in file under `config/`.

## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
