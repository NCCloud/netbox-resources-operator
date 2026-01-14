CLUSTER ?= netbox-resources-operator
UV ?= uv
KIND ?= kind
DOCKER ?= docker
DOCKER_ARGS ?= --load
APP_NAME ?= ghcr.io/nccloud/netbox-resources-operator
TAG ?= 0.1.0-dev
IMG ?= ${APP_NAME}:${TAG}
KIND_IMAGE ?= kindest/node:v1.35.0

.PHONY: help
help: ## show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: docker-build
docker-build: ## Build docker image.
	$(DOCKER) buildx build -t $(IMG) . $(DOCKER_ARGS)

.PHONY: docker-load
docker-load: ## Load docker image in KIND.
	$(KIND) load docker-image --name $(CLUSTER) $(IMG)

.PHONY: cluster
cluster: ## Create a single node kind cluster.
	$(KIND) create cluster --name $(CLUSTER) --image $(KIND_IMAGE)

.PHONY: cluster-delete
cluster-delete: ## Delete the kind cluster.
	$(KIND) delete cluster --name $(CLUSTER)

.PHONY: docker-all
docker-all: docker-login image docker-push ## login to registry, build an image and push it

.PHONY: crds
crds: ## generate local crds
	@uv run crd.py

.PHONY: init-project
init-project: ## create a venv and install packages using uv
	@uv sync --locked

.PHONY: test
test: init-project ## run tests
	@NETBOX_APP_ENV=test uv run coverage run --source="app" -m unittest discover tests && uv run coverage report

.PHONY: lint
lint: init-project ## run linter
	uv run ruff check
