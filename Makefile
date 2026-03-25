XMLLINT := $(shell command -v xmllint 2>/dev/null)

ifdef XMLLINT
ADDON_ID      := $(shell xmllint --xpath 'string(/addon/@id)' addon.xml)
ADDON_VERSION := $(shell xmllint --xpath 'string(/addon/@version)' addon.xml)
else
ADDON_ID      := $(shell awk '/^<addon/{found=1} found{while(match($$0,/[a-z-]+="[^"]*"/)){attr=substr($$0,RSTART,RLENGTH); $$0=substr($$0,RSTART+RLENGTH); if(attr~/^id=/){gsub(/id="|"/,"",attr);id=attr}}} found && />/{print id; exit}' addon.xml)
ADDON_VERSION := $(shell awk '/^<addon/{found=1} found{while(match($$0,/[a-z-]+="[^"]*"/)){attr=substr($$0,RSTART,RLENGTH); $$0=substr($$0,RSTART+RLENGTH); if(attr~/^version=/){gsub(/version="|"/,"",attr);ver=attr}}} found && />/{print ver; exit}' addon.xml)
endif

ZIP_NAME  := $(ADDON_ID)-$(ADDON_VERSION).zip
BUILD_DIR := build
ROOT_DIR  := $(ADDON_ID)

RSYNC_EXCLUDES := \
	--exclude='.git' \
	--exclude='.venv' \
	--exclude='.vscode' \
	--exclude='__pycache__' \
	--exclude='*.pyc' \
	--exclude='*.pyo' \
	--exclude='*.DS_Store' \
	--exclude='Makefile' \
	--exclude='$(BUILD_DIR)'

.PHONY: all build clean info

all: build

build: clean
	@echo ">>> Plugin  : $(ADDON_ID)"
	@echo ">>> Version : $(ADDON_VERSION)"
	@echo ">>> Output  : $(BUILD_DIR)/$(ZIP_NAME)"
	@mkdir -p "$(BUILD_DIR)/$(ROOT_DIR)"
	@rsync -a . "$(BUILD_DIR)/$(ROOT_DIR)" $(RSYNC_EXCLUDES)
	@cd "$(BUILD_DIR)" && zip -r "$(ZIP_NAME)" "$(ROOT_DIR)" > /dev/null
	@rm -rf "$(BUILD_DIR)/$(ROOT_DIR)"
	@echo ">>> Ready!  $(BUILD_DIR)/$(ZIP_NAME)"

clean:
	@rm -rf "$(BUILD_DIR)"
	@echo ">>> Build folder removed."

info:
	@echo "Addon-id : $(ADDON_ID)"
	@echo "Version  : $(ADDON_VERSION)"
	@echo "Zip-name : $(ZIP_NAME)"
