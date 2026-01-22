PY=python3
PIP=pip

.PHONY: install dev fmt lint test compose-up compose-down migrate seed bench

install:
	$(PIP) install -r requirements.txt

dev:
	uvicorn app.main:app --reload

fmt:
	black .
	ruff check --fix . || true

lint:
	ruff check .

test:
	pytest -q

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v

migrate:
	alembic upgrade head

seed:
	$(PY) scripts/seed_demo.py

bench:
	$(PY) scripts/bench.py
