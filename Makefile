.PHONY: all build lint requirements setup test

all: up

build:
	docker compose build

clean:
	docker compose down -v --remove-orphans

cypress:
	# Turn on local system, and open cypress in interactive mode
	docker compose up -d && cd e2e && npm install && npm run test

debug:
	# Stop the canonical ckan container to avoid a port collision. Use `run`
	# so that we have interactive console access for the debugger.
	docker compose stop ckan ; docker compose run --service-ports ckan

requirements:
	docker compose run --rm -T ckan /app/bin/requirements.sh

lint:
	flake8 . --count --show-source --statistics

restart:
	docker compose restart ckan

test-build:
	docker compose -f docker-compose.yml -f docker-compose.test.yml build

test:
	docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit test

test_extension:
	docker compose run --rm -T ckan pytest --cov=ckanext.datagov_inventory --disable-warnings /app/ckanext/datagov_inventory/tests/

up:
	docker compose up $(ARGS)

clear-solr-volume:
	# Destructive
	docker stop $(shell docker volume rm catalogdatagov_solr_data 2>&1 | cut -d "[" -f2 | cut -d "]" -f1)
	docker rm $(shell docker volume rm catalogdatagov_solr_data 2>&1 | cut -d "[" -f2 | cut -d "]" -f1)
	docker volume rm catalogdatagov_solr_data

unlock-solr-volume:
	# Corruptible
	docker compose run solr /bin/bash -c "rm -rf /var/solr/data/ckan/data/index/write.lock"
