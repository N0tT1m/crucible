.PHONY: up down logs ps clean nuke ch-init dbt-deps dbt-build dbt-test seed-vault build run smoke help

# ---- stack ----
up:                    ## docker compose up
	docker compose -f deploy/docker-compose.yml up -d --build

down:                  ## docker compose down (preserves volumes)
	docker compose -f deploy/docker-compose.yml down

logs:                  ## tail all logs
	docker compose -f deploy/docker-compose.yml logs -f

ps:
	docker compose -f deploy/docker-compose.yml ps

clean:                 ## stop + delete volumes
	docker compose -f deploy/docker-compose.yml down -v

nuke: clean            ## clean + delete built images
	docker rmi redboxq 2>/dev/null || true

# ---- ClickHouse / dbt ----
ch-init:               ## apply migrations/*.sql in order
	./scripts/init_clickhouse.sh

dbt-deps:
	cd dbt && dbt deps

dbt-build:             ## run + test all dbt models
	cd dbt && dbt build

dbt-test:
	cd dbt && dbt test

seed-vault:            ## regenerate seeds/dim_payload.csv from redbox/payloads/vault
	python3 scripts/seed_dim_payload.py \
	  --vault ../redbox/payloads/vault \
	  --out dbt/seeds/dim_payload.csv

# ---- Go service ----
build:
	cd cmd/redboxq && go build -o ../../bin/redboxq .

run:
	go run ./cmd/redboxq

# ---- smoke ----
smoke:                 ## quick end-to-end check (assumes `up` already)
	@echo "==> ClickHouse ping"
	@curl -sf 'http://localhost:8123/ping'
	@echo
	@echo "==> redboxq /health"
	@curl -sf localhost:7000/health | jq

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "} {printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'
