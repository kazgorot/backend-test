.PHONY: run fmt lint list_strict lint_fix migrate ps up db-up db-login db-rm db-stop

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

up:
	docker compose up -d

run: db-up
	cd app && POSTGRES_PORT=${POSTGRES_LOCAL_PORT} POSTGRES_HOST=${POSTGRES_LOCAL_HOST} poetry run uvicorn schema:app --reload

fmt:
	cd app && ruff check -s --fix --exit-zero .

lint list_strict:
	cd app && poetry run mypy .
	cd app && poetry run ruff check .

lint_fix:
	cd app && poetry fmt lint

migrate:
	docker compose up -d db
	poetry run python -m yoyo apply -vvv --batch --database "postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_LOCAL_HOST}:${POSTGRES_LOCAL_PORT}/${POSTGRES_DB_NAME}" ./migrations

ps:
	docker compose ps

db-up:
	docker compose up -d db

db-stop:
	docker compose stop db
db-login:
	docker compose exec -it db psql -U postgres -d books

db-rm:
	docker compose up -d db
	docker compose exec db sh -c 'rm -rf /var/lib/postgresql/data/*'
	docker compose exec db ls /var/lib/postgresql/data/
	docker compose rm -v -s db
