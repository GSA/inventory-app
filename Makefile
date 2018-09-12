.PHONY: all build copy-src local requirements setup test update-dependencies

CKAN_HOME := /usr/lib/ckan

all: build

build:
	docker-compose build

local:
	docker-compose -f docker-compose.yml -f docker-compose.local.yml up

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt

update-dependencies:
	docker-compose run --rm app ./install-dev.sh

copy-src:
	docker cp inventory-app_app_1:$(CKAN_HOME)/src .

test:
	docker-compose build
