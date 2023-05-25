IMAGE_TAG  := $$(git rev-parse --short HEAD)
IMAGE_NAME := gcr.io/ox-registry-prod/prebid/prebid-optimizer-config-generator

help: ## Show this help
help:
	@grep -E '^[a-zA-Z0-9._-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image
build:
	docker build -t prebid-optimizer-config-generator:latest -f docker/Dockerfile .

shell: ## Run Docker image
shell:
	docker run -it \
		-e GOOGLE_CLOUD_PROJECT=ox-datascience-devint \
		-v $(PWD):/app \
		-v ${HOME}/.config/:/root/.config \
		prebid-optimizer-config-generator:latest bash

# --- Dev work ---

build.dev: ## Build dev Docker image
build.dev:
	docker build -t prebid-optimizer-config-generator-dev:latest -f docker/dev.Dockerfile .

shell.dev: ## Run dev Docker image (for testing)
shell.dev:
	docker run -it \
		-e GOOGLE_CLOUD_PROJECT=ox-datascience-devint \
		-v $(PWD):/app \
		-v ${HOME}/.config/:/root/.config \
		prebid-optimizer-config-generator-dev:latest bash

docker.jupyter: ## Start jupyter notebook
docker.jupyter:
	docker run -it --rm \
		--entrypoint "/app/start_jupyter.sh" \
		-v ${HOME}/.config:/root/.config \
		-v $(PWD):/app \
		-p 9999:9999 \
		prebid-optimizer-config-generator-dev:latest

test: ## Test models (run after `make shell.dev`)
test:
	pytest -v

# --- Used by CI-CD ---

source-version:
	@echo ${IMAGE_TAG}

image-name:
	@echo ${IMAGE_NAME}
