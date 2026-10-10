PYTHON ?= .venv/bin/python
PORT ?= 8000
.PHONY: help install test check build run dev clean check-env backup
help:
	@echo "GoalSift: install | check | build | run | dev | backup | clean"
install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.lock
	cd frontend && npm ci

test:
	$(PYTHON) -m pytest
check: test
	cd frontend && npm run lint && npm run build
build:
	cd frontend && npm run build
run: build
	PYDANTIC_AI_NO_BANNER=1 $(PYTHON) -m uvicorn goalsift.app:app --host 127.0.0.1 --port $(PORT)
# Start `make run` in another terminal first. Vite forwards /api to port 8000.
dev:
	cd frontend && npm run dev
backup:
	$(PYTHON) -m scripts.backup
check-env:
	$(PYTHON) -c "from goalsift.paths import sanctioned_data_root; print('data root:', sanctioned_data_root())"
# Application data is intentionally preserved.
clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache frontend/dist
