.PHONY: help
help: ## show help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: docker-build
docker-build: ## Build docker image
	@./helper.sh build_operator_image

.PHONY: docker-build-load
docker-build-load: ## Build a docker image and load it in a kind cluster
	@./helper.sh build_and_load_operator_image

.PHONY: cluster
cluster: ## Create a single node kind cluster
	@./helper.sh create_kind_cluster

.PHONY: prepare-dev-environment
prepare-dev-environment: ## Prepare the development environment
	@./helper.sh prepare_dev_environment

.PHONY: cluster-delete
cluster-delete: ## Delete the kind cluster
	@./helper.sh delete_kind_cluster

.PHONY: crds
crds: ## generate local crds
	@uv run crd.py

.PHONY: init-project
init-project: ## create a venv and install packages using uv
	@uv sync --locked

.PHONY: test-unit
test-unit: init-project ## run unit tests
	@NETBOX_APP_ENV=test uv run coverage run --source="app" -m unittest discover tests/unit && uv run coverage report

.PHONY: test-e2e
test-e2e: init-project ## run e2e tests
	@uv run pytest -vv tests/e2e

.PHONY: lint
lint: init-project ## run linter
	uv run ruff check
