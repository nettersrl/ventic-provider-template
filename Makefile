VENTIC = $(shell python3 scripts/sources.py backend)
BINARY_VENTIC = $(shell python3 scripts/binary-release.py path)
PYTHON ?= $(VENTIC)/.venv/bin/python
ENVIRONMENT ?= staging
FRONTEND ?= portal
BACKEND ?= none
DEV_PORT ?= 5175
COMPONENTS ?= auto
SANDBOX_PROFILE := $(CURDIR)/config/sandbox.yaml

.PHONY: help sources-fetch stack-check test deploy-plan deploy-release deploy-verify version version-set setup sandbox-up sandbox-status sandbox-verify sandbox-down sandbox-destroy sandbox-sync sandbox-reset sandbox-dev sandbox-backend sandbox-trust
help:
	@printf '%s\n' 'Binary installation: python3 -m pip install -r requirements-installer.txt; make release-fetch | release-check | deploy-plan | deploy-release'
	@printf '%s\n' 'make backup-init | backup-full | backup-incremental | backup-list | backup-verify | restore-plan [ARGS=--include-s3]'
	@printf '%s\n' 'make sources-fetch | stack-check | test' 'make deploy-plan ENVIRONMENT=staging' 'make deploy-release ENVIRONMENT=staging (signed, licensed release)' 'make version | version-set VERSION=MAJOR.MINOR.PATCH' 'make sandbox-up | sandbox-dev | sandbox-down'
sources-fetch:
	python3 scripts/sources.py fetch
.PHONY: release-fetch release-check
release-fetch:
	python3 scripts/binary-release.py fetch
release-check:
	python3 scripts/binary-release.py verify
stack-check:
	python3 scripts/sources.py check
test:
	$(PYTHON) -m unittest discover -s tests -v
deploy-plan:
	python3 scripts/deploy.py plan --environment "$(ENVIRONMENT)"
deploy-release:
	python3 scripts/deploy.py deploy --environment "$(ENVIRONMENT)"
deploy-verify:
	python3 scripts/deploy.py verify --environment "$(ENVIRONMENT)"
setup:
	$(MAKE) -C "$(VENTIC)" local-setup
version:
	@cat VERSION
version-set:
	python3 scripts/provider-version.py --version "$(VERSION)"
sandbox-up sandbox-status sandbox-verify sandbox-down sandbox-destroy sandbox-sync sandbox-reset sandbox-dev sandbox-backend sandbox-trust: setup
	$(MAKE) -C "$(VENTIC)" $@ SANDBOX_PROFILE="$(SANDBOX_PROFILE)" FRONTEND="$(FRONTEND)" BACKEND="$(BACKEND)" DEV_PORT="$(DEV_PORT)" COMPONENTS="$(COMPONENTS)" CONFIRM="$(CONFIRM)" ARGS="$(ARGS)"

# Private recovery material stays in this checkout, outside Git and release artifacts.
BACKUP_CONFIG ?= $(CURDIR)/private/backup.json
.PHONY: backup-init backup-full backup-incremental backup-list backup-verify restore-plan
backup-init:
	$(PYTHON) scripts/backup.py init --config "$(BACKUP_CONFIG)" $(ARGS)
backup-full:
	$(PYTHON) scripts/backup.py full --config "$(BACKUP_CONFIG)" $(ARGS)
backup-incremental:
	$(PYTHON) scripts/backup.py incremental --config "$(BACKUP_CONFIG)" $(ARGS)
backup-list:
	$(PYTHON) scripts/backup.py list --config "$(BACKUP_CONFIG)" $(ARGS)
backup-verify:
	$(PYTHON) scripts/backup.py verify --config "$(BACKUP_CONFIG)" $(ARGS)
restore-plan:
	$(PYTHON) scripts/backup.py restore-plan --config "$(BACKUP_CONFIG)" $(ARGS)
