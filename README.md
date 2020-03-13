[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

# inventory-app

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies._


## Development


### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)


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

#### Update dependencies
To update the dependencies from various libraries (usually handled by running build),
run the following:

    $ make update-dependencies

Update lock file for dependencies. **Because of a version conflict for
repoze.who, special care should be taken to make sure that repoze.who==1.0.18 is
shipped to production in order to be compatible with ckanext-saml2. After
generating the requirements-freeze.txt, manually review the file to make sure
the versions are correct. See https://github.com/GSA/catalog-app/issues/78 for
more details.**

    $ make requirements

This freezes the requirements at `requirements-freeze.txt`, and should only be done
when tests are passing locally. CircleCi will run the build against this 
`requirements-freeze.txt` file to validate that the code should work in production.


### Live Editing

To edit CKAN or extension code live, the attached volume needs to be found and used.

You can find the volume by running `docker volume ls`, but the default is `inventoryapp_ckan`. You can then run `docker volume inspect inventoryapp_ckan` to get the location details on your local machine. You may need to edit permissions to this folder to edit under your current user. Once this is complete, use your preferred editor to manage the code as needed.

If you restart the service, the volume stays live. It must be removed manually. If you make edits and want to revert, you can run `docker volume rm -f inventoryapp_ckan`. The docker containers need to be stopped and removed before you can run this command.

### Tests

    $ make test

## Deploying to cloud.gov

Copy `vars.yml.template` to `vars.yml`, and customize the values in that file. Then, assuming you're logged in for the Cloud Foundry CLI:

Update and cache all the Python package requirements

```sh
./vendor_requirements.sh
```

Create the database used by datastore. `((appname))` should be the same as what you have in vars.yml.

```sh
$ cf create-service aws-rds medium-psql ((app_name))-datastore
```

Create the database used by CKAN itself. You have to wait a bit for the datastore DB to be available. (See [the cloud.gov instructions on how to know when it's up](https://cloud.gov/docs/services/relational-database/#instance-creation-time).)
```sh
$ cf create-service aws-rds shared-psql ((app_name))-db
```

Deploy the Solr instance and the app.
```sh
$ cf push --vars-file vars.yml
```

Ensure the inventory app can reach the Solr app.
```sh
$ cf add-network-policy ((app_name)) --destination-app ((app_name))-solr --protocol tcp --port 8983
```

You should now be able to visit `https://[ROUTE]`, where `[ROUTE]` is the route reported by `cf app ((app_name))`.

### Remaining concerns for cloud.gov deployment

* The `repoze.who` workaround in the `cfstart.sh` file shouldn't be necessary
* We haven't gone past "It responds with a recognizable page!"
  * We need to sort out how authentication should work, and document that.
  * Test, test, test, test that everything works as expected.
* The memory per instance should be right-sized.
* Staging and production deployments should be driven entirely via CI, including vendoring of dependencies.
  * The branch `adborden/cloud.gov` includes the start of this work
* Production should deploy at least two instances of the app for durability.
* Production should use a non-shared PGSQL instance for durability.
* Production databases should have a CI-driven process for making dumps into an S3 bucket.
* The Solr instance deployed in this manifest is not suitable for production use because Solr \
  requires a durable local filesystem for persistence. cloud.gov can't supply that, so the Solr \
  deployment for production will need to be outside of cloud.gov. Changes to the instructions: 
  * Only push the inventory-app: `cf push --vars-file vars.yml ((app_name))`
  * Set the SOLR_URL explicitly: `cf set-env ((app_name)) SOLR_URL &lt;the-solr-url&gt;`

## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
