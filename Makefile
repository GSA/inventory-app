.PHONY: all build requirements setup test update-dependencies

CKAN_HOME := /usr/lib/ckan

all: up

build:
	docker-compose build

clean:
	docker-compose down -v

local:
	docker-compose -f docker-compose.yml -f docker-compose.local.yml up

make reload: stop-web start-web

start-web:
	docker-compose up app

stop-web:
	docker-compose exec app pkill -f gunicorn

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml build
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml build --build-arg REQUIREMENTS_FILE app
	docker-compose -f docker-compose.yml -f docker-compose.test.yml -f docker-compose.seed.yml up --abort-on-container-exit test

up:
	docker-compose up -d

up-with-data:
	docker-compose -f docker-compose.yml -f docker-compose.seed.yml build
	docker-compose -f docker-compose.yml -f docker-compose.seed.yml up

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt
