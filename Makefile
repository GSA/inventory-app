.PHONY: all build lint requirements setup test update-dependencies

all: up

build:
	docker-compose build

clean:
	docker-compose down -v --remove-orphans

cypress:
	# Turn on local system, and open cypress in interactive mode
	CYPRESS_USER=cypress-user CYPRESS_USER_PASSWORD=cypress-user-password docker-compose up -d && cd e2e && CYPRESS_BASE_URL=http://localhost:5000 npx cypress open

debug:
	# Stop the canonical app container to avoid a port collision. Use `run`
	# so that we have interactive console access for the debugger.
	docker-compose stop app ; docker-compose run --service-ports app

requirements:
	docker-compose run --rm -T app /app/bin/requirements.sh

lint:
	flake8 . --count --show-source --statistics

restart:
	docker-compose restart app

test-build:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml build

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit test

test_extension:
	docker-compose run --rm app nosetests --ckan --with-pylons=docker_test.ini ckanext/datagov_inventory/tests/*

up:
	docker-compose up

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt
