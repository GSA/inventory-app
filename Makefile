.PHONY: all build requirements setup test update-dependencies

all: build

build:
	docker-compose build

requirements:
	docker-compose run --rm -T app pip --quiet freeze > requirements-freeze.txt

update-dependencies:
	docker-compose run --rm app pip install -r requirements.txt

test:
	docker-compose build
