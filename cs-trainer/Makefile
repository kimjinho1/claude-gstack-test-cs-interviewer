.PHONY: dev install backend frontend test

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
