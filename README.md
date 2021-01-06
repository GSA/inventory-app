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

To edit CKAN or extension code live, the local code needs to be attached via a volume.
Add a local extension folder path into the `docker-compose.yml` file that you would like to edit
(see volume section for commented example).
After editing the extension/ckan core (see below), run `make debug` to restart the application 
and evaluate the edits/debugging.

_TODO: tested `--reload` functionality of gunicorn, but does not work well with paster flag._
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
`production.ini` file (`debug = true`), which gives some UI tools on the webpage to parse stack
traces and various other examination tools. The behavior is inconsistent, probably due to
ckan serving pages as pylons sometimes and flask at others.

**Make sure you remove all pdb statements before commiting to any repository!**

### Tests

    $ make test


## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
