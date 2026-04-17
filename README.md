# inventory-app

[![GitHub Actions](https://github.com/GSA/inventory-app/actions/workflows/deploy.yml/badge.svg)](https://github.com/GSA/inventory-app/actions/workflows/deploy.yml)

A [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).

For details on the system architecture, please see our [data.gov systems list](https://github.com/GSA/data.gov/blob/main/SYSTEMS.md).

## Development

### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)
- [Cloud Foundry](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html) CLI v7

### Getting started

Build and bring up the containers.

    make up
    make up-with-data  # Gives development environment basic user, organization, and dataset

Open CKAN to verify it's working:

    open http://localhost:5000

If you would like to seed data into the system, examine the test framework (`e2e/cypress/support/command.js`) for some examples of creating organizations and/or datasets with resources.

### docker compose commands

To enter into the app container in interactive mode as root:

    docker compose exec app /bin/bash

To run a one off command inside the container:

    docker compose exec app {command}

### Update dependencies

Update the "lock" file for dependencies.

    make build requirements

This freezes the requirements at `requirements.txt`. Run the tests with the updated dependencies.

    make test

### Live Editing

To edit CKAN or extension code live, the local code needs to be attached via a volume. Add a local extension folder path into the `docker-compose.yml` file that you would like to edit (see volume section for commented example). After editing the extension/ckan core, run `make up` then run `make debug` to restart the application with an interactive console.

#### Debugger

Add `import ipdb; ipdb.set_trace()` as a new line where you would like to start debugging. Then run `make debug`. Once the debugger statement is triggered, a command prompt should display in the console. See [documentation](https://docs.python.org/3/library/pdb.html#debugger-commands) for available commands.

**Make sure you remove all pdb statements before committing to any repository!**

### Tests

    make test

The tests utilize Cypress. To fully install and rapidly iterate on tests, install Cypress locally:

    npm install cypress

Then run `make cypress` to turn on Cypress in interactive mode.

Please be aware that the tests attempt to clean themselves after each spec file. If the system is in a bad state, run `make clean` to restart in a clean environment.

## Deploying to cloud.gov

Copy `vars.yml.template` to `vars.yml` and customize the values. Then, assuming you're logged in to the Cloud Foundry CLI:

Create the database used by datastore:

    cf create-service aws-rds micro-psql ${app_name}-datastore --wait

Create the database used by CKAN itself:

    cf create-service aws-rds small-psql ${app_name}-db --wait

Create the S3 bucket for data storage:

    cf create-service s3 basic-sandbox ${app_name}-s3 --wait

Create the Redis service for cache:

    cf create-service aws-elasticache-redis redis-dev ${app_name}-redis --wait

Deploy the Solr instance:

    cf push --vars-file vars.yml ${app_name}-solr --wait

Create the secrets service:

    cf create-user-provided-service ${app_name}-secrets

Deploy the CKAN app:

    cf push --vars-file vars.yml ${app_name}

Ensure the inventory app can reach the Solr app:

    cf add-network-policy ${app_name} ${app_name}-solr --protocol tcp --port 8983

### Secrets

| Name | Description | Where to find |
|------|-------------|---------------|
| CKAN___BEAKER__SESSION__SECRET | Session secret for encrypting CKAN sessions | `pwgen -s 32 1` |
| CKAN___WTF_CSRF_SECRET_KEY | CSRF secret for generating CSRF tokens | `pwgen -s 32 1` |
| DS_RO_PASSWORD | Read-only password for the datastore user | Initially randomly generated |
| NEW_RELIC_LICENSE_KEY | New Relic license key | New Relic account settings |
| SAML2_PRIVATE_KEY | Base64 encoded SAML2 key matching the Login.gov certificate | Data.gov DevSecOps Google Drive |

To update secrets:

    cf update-user-provided-service ${app_name}-secrets -p "CKAN___BEAKER__SESSION__SECRET, CKAN___WTF_CSRF_SECRET_KEY, DS_RO_PASSWORD, NEW_RELIC_LICENSE_KEY, SAML2_PRIVATE_KEY"

### CI configuration

Create a GitHub environment for each application you're deploying, configured with the following secrets:

| Secret name | Description |
|-------------|-------------|
| CF_SERVICE_AUTH | The service key password |
| CF_SERVICE_USER | The service key username |

## Login.gov integration

We use Login.gov as our SAML2 Identity Provider (IdP). Production apps use the production Login.gov instance while other apps use the Login.gov identity sandbox.

Each year in March, Login.gov rotates their credentials. See [Login.gov SAML certificate rotation steps](https://github.com/GSA/data.gov/wiki/Login.gov-SAML-certificate-rotation-steps) for details.

Our Service Provider (SP) certificate and key are provided through environment variable and user-provided service. The Login.gov IdP metadata is stored in file under `config/`.

## Adding Organizations, Publishers, and Users

See [inventory.data.gov wiki page](https://github.com/GSA/data.gov/wiki/inventory.data.gov).

## License and Contributing

We're glad you're thinking about contributing to Data.gov! Before contributing, please read our [CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and this README.

For questions, email the Data.gov team at [datagov@gsa.gov](mailto:datagov@gsa.gov).
