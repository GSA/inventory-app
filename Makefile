.PHONY: all build lint requirements setup test update-dependencies

all: up

build:
	docker-compose build

clean:
	docker-compose down -v --remove-orphans

debug:
	# Stop the canonical app container to avoid a port collision. Use `run`
    # so that we have interactive console access for the debugger.
	docker-compose stop app ; docker-compose run --service-ports app

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt

lint:
	flake8 . --count --show-source --statistics

restart:
	docker-compose restart app

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml build
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml build --build-arg REQUIREMENTS_FILE app
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml up --abort-on-container-exit test

test_extension:
	docker-compose run --rm app nosetests --ckan --with-pylons=docker_test.ini ckanext/datagov_inventory/tests/*

up:
	docker-compose up

up-with-data:
	docker-compose -f docker-compose.yml -f docker-compose.seed.yml build
	docker-compose -f docker-compose.yml -f docker-compose.seed.yml up

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt
