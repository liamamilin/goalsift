.PHONY: help test test-verbose clean check-env

help:
	@echo "GoalSift (Phase A) targets:"
	@echo "  test         run pytest (isolated, no user files touched)"
	@echo "  test-verbose run pytest with -v"
	@echo "  check-env    show resolved env / data root (does not print secrets)"
	@echo "  clean        remove local .goalsift_data and caches"

test:
	python3 -m pytest

test-verbose:
	python3 -m pytest -v

check-env:
	@python3 -c "from goalsift.paths import sanctioned_data_root; print('data root:', sanctioned_data_root())"
	@echo "GOALSIFT_DATA_DIR set? $${GOALSIFT_DATA_DIR:-no}"
	@echo "(secrets are never printed by this target)"

clean:
	rm -rf .goalsift_data .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
