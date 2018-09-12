# inventory-app

[![CircleCI](https://circleci.com/gh/GSA/inventory-app.svg?style=svg)](https://circleci.com/gh/GSA/inventory-app)

Is a [Docker](https://www.docker.com/)-based [CKAN](http://ckan.org) deployment. CKAN is used by Data.gov @ https://inventory.data.gov

_Note: this is currently a work in progress. We're mainly using this to manage
the `requirements-freeze.txt` for production dependencies. Very little works beyond that.`_


## Development


### Prerequisites

- [Docker and Docker Compose](https://docs.docker.com/compose/)


### Getting started

Build and bring up the containers.

    $ docker-compose up


### Docker-compose commands

To enter into the container in interactive mode as root:

    $ docker-compose run app /bin/bash

To run a one off command inside the container:

    $ docker-compose run app {{command}}


### Source Code Folder (**src**)

**Note:** follow these steps only if your src folder is empty or you need the latest code

1. Start the app, from root folder.

    $ docker-compose up

1. Copy app source files to your local src folder.

    $ make copy-src

1. Stop the app: `docker-compose down`


### Workflow

1. Start the app in local mode.

    $ make local

1. Make changes to the source code in `src`.
1. Commit the changes, and push extensions to GitHub.
1. (optional) Pull in the latest dependencies, including nested dependencies.

    $ make update-dependencies

1. Update the pinned requirements in `requirements-freeze.txt`.

    $ make requirements

see: https://blog.engineyard.com/2014/composer-its-all-about-the-lock-file
the same concepts apply to pip.


### Tests

    $ make test


## License and Contributing

We're so glad you're thinking about re-using and/or contributing to Data.gov!

Before contributing to Data.gov we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
