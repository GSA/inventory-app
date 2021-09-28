.PHONY: all build lint requirements setup test update-dependencies

all: up

build:
	docker-compose build

clean:
	docker-compose down -v --remove-orphans

cypress:
	# Turn on local system, and open cypress in interactive mode
	docker-compose up -d && cd e2e && npm install && npm run test

debug:
	# Stop the canonical ckan container to avoid a port collision. Use `run`
	# so that we have interactive console access for the debugger.
	docker-compose stop ckan ; docker-compose run --service-ports ckan

requirements:
	docker-compose run --rm -T ckan /app/bin/requirements.sh

lint:
	flake8 . --count --show-source --statistics

restart:
	docker-compose restart ckan

test-build:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml build

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit test

test_extension:
	docker-compose exec ckan pytest --cov=ckanext.datagov_inventory --disable-warnings /app/ckanext/datagov_inventory/tests/

up:
	docker-compose up
