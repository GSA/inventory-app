[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

# inventory-app

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies. Very little works beyond that._


## Development


### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)
- [Cloud Foundry](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html) CLI v7


### Getting started

Build and bring up the containers.

    $ make up
    $ make up-with-data [_Gives development environment basic user, organization, and dataset_]

You may optionally seed the inventory with a default user, organization, and dataset by running the following command in the folder while the docker-compose is still up and has finished running:

    $ docker-compose exec app /opt/inventory-app/seed.sh

_If the user is already created and you would like to rebuild the organization and dataset, you can specify the API key as a second argument to the execution: `docker-compose exec app /opt/inventory-app/seed.sh long-api-key`_

Open CKAN to verify it's working

    $ open http://localhost:5000

### Docker-compose commands

To enter into the app container in interactive mode as root, you will need to run the following:

    $ docker-compose exec app /bin/bash

To run a one off command inside the container:

    $ docker-compose exec app {command}


### Update dependencies

Update the "lock" file for dependencies.

    $ make build requirements

This freezes the requirements at `requirements.txt`. Run the tests with the
updated dependencies.

    $ make test


### Live Editing

To edit CKAN or extension code live, the local code needs to be attached via a volume.
Add a local extension folder path into the `docker-compose.yml` file that you would like to edit
(see volume section for commented example).
After editing the extension/ckan core (see below), run `make up` (the app will not start appropriately)
then run `make debug` to restart the application with an interactive console.

_TODO: tested `--reload` functionality of gunicorn, but [does not work well with paster flag](https://docs.gunicorn.org/en/stable/settings.html#reload)._
_Hopefully this option improves in the future._

#### Debugger

Add `import ipdb; ipdb.set_trace()` as a new line where you would like to start debugging.
Then run `make debug`, and a new instance of the ckan app will be started that has an 
interactive console. Once the debugger statement is triggered, then a command prompt 
should display in the console. See [documentation](https://docs.python.org/3/library/pdb.html#debugger-commands)
for available commands. `ipdb` is preferred for styling/readability reasons, but `pdb` will
work as well. `web-pdb` was tested, but has various timing complications of it's own that causes
unnecessary complications and failures.

The flask debugger is also imported as a dev requirement and turned on by default in the
`development.ini` file (`debug = true`), which gives some UI tools on the webpage to parse stack
traces and various other examination tools. The behavior is inconsistent, probably due to
ckan serving pages as pylons sometimes and flask at others.

**Make sure you remove all pdb statements before commiting to any repository!**

### Tests

    $ make build test_extension test


## Deploying to cloud.gov

Copy `vars.yml.template` to `vars.yml`, and customize the values in that file. Then, assuming you're logged in for the Cloud Foundry CLI:

Update and cache all the Python package requirements

```sh
./vendor-requirements.sh
```

Create the database used by datastore. `${app_name}` should be the same as what you have in vars.yml.

```sh
$ cf create-service aws-rds micro-psql ${app_name}-datastore
```

Create the database used by CKAN itself. You have to wait a bit for the datastore DB to be available (see [the cloud.gov instructions on how to know when it's up](https://cloud.gov/docs/services/relational-database/#instance-creation-time)).

    $ cf create-service aws-rds small-psql ${app_name}-db -c '{"version": 11}'

Create the s3 bucket for data storage.

    $ cf create-service s3 basic-sandbox ${app_name}-s3

Create the Redis service for cache

    $ cf create-service aws-elasticache-redis redis-dev ${app_name}-redis

Create the secrets service to store secret environment variables (current list)

    $ cf cups ${app_name}-secrets -p "DS_RO_PASSWORD, NEW_RELIC_LICENSE_KEY"

Deploy the Solr instance.

    $ cf push --vars-file vars.yml ${app_name}-solr

Deploy the CKAN app.

    $ cf push --vars-file vars.yml ${app_name}

Ensure the inventory app can reach the Solr app.

    $ cf add-network-policy ${app_name} ${app_name}-solr --protocol tcp --port 8983

You should now be able to visit `https://[ROUTE]`, where `[ROUTE]` is the route reported by `cf app ${app_name}`.


### CI configuration

Create a GitHub environment for each application you're deploying. Each
GH environment should be configured with secrets from a [ci-deployer service
account](https://github.com/GSA/datagov-deploy/wiki/Cloud.gov-Cheat-Sheet#space-organization).

Secret name | Description
----------- | -----------
CF_SERVICE_AUTH | The service key password.
CF_SERVICE_USER | The service key username.


## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
