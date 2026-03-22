.PHONY: dev install backend frontend test up down build logs

# Docker Compose commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

install:
	cd frontend && npm install
	pip install -r backend/requirements.txt

backend:
	uvicorn backend.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 backend frontend

test-backend:
	python -m pytest backend/tests/ -v

test-frontend:
	cd frontend && npm test

test:
	$(MAKE) test-backend test-frontend

ollama-pull:
	ollama pull llama3.1:8b
