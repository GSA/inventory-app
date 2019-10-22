[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

# inventory-app

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) development environment for [inventory.data.gov](https://inventory.data.gov).

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies. Very little works beyond that.`_


## Development


### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)


### Getting started

Build and bring up the containers.

    $ make up

Create an admin user. You'll be prompted for a password.

    $ docker-compose run --rm app paster --plugin=ckan sysadmin add admin -c /etc/ckan/production.ini


### Docker-compose commands

To enter into the container in interactive mode as root:

    $ docker-compose run app bash

To run a one off command inside the container:

    $ docker-compose run app <command>

Update dependencies.

    $ make update-dependencies

Update lock file for dependencies.

    $ make requirements


### Tests

    $ make test


## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
