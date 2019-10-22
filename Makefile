.PHONY: all build requirements setup test update-dependencies

all: up

build:
	docker-compose build

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt


test:
	docker-compose build

up:
	docker-compose up

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt
