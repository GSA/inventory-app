[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

# inventory-app

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies. Very little works beyond that._


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
Need to avoid pulling in dev requirements, so start from a clean build
(without starting up the app) and save the requirements.

    $ make clean build requirements

This freezes the requirements at `requirements-freeze.txt`, and should only be done
when tests are passing locally. CircleCi will run the build against this 
`requirements-freeze.txt` file to validate that the code should work in production.


### Live Editing

To edit CKAN or extension code live, the attached volume needs to be setup correctly.

Add a local extension folder via the docker-compose.yml file (see volume comment for example).

After editing code, run `make restart` to restart the application and evaluate the edits/debugging

_TODO: tested `--reload` functionality of gunicorn, but does not work well with paster flag. Hopefully this option improves in the future._

#### Web Debugger

To step through code and examine variables, you can use [web-pdb](https://pypi.org/project/web-pdb/).
Add/edit the variable located at `.env` (you can create the file from `.env.sample`) called 
`LOCAL_EXT` to be the local path to the extension you would like to examine.
Then add/edit the variable `EXT_PATH` to be the container path to the extension you are overriding.
Finally, edit the `docker-compose.yml` file and uncomment the volume line utilizing those variables.

The `start.sh` script will make sure the python code is installed properly, and you should be able to add
debug statements and/or make edits in the local repository to test changes in real time.

**Make sure you remove all web-pdb statements before commiting to any repository!**

### Tests

    $ make test


## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
