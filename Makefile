.PHONY: all build requirements setup test update-dependencies

all: up

build:
	docker-compose build

clean:
	docker-compose down -v --remove-orphans

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt

test:
	docker-compose -f docker-compose.yml -f docker-compose.test.yml build
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit test

up:
	docker-compose up

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt
