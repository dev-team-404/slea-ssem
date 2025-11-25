# ============================================================
# SLEA-SSEM Makefile
# Docker & docker-compose 기반 개발 환경 관리
# 동료 피드백 반영: 간결함 + Proxy 자동 주입 + TDD
# ============================================================

SHELL := /bin/bash
.ONESHELL:
.PHONY: help init build up down restart logs ps shell shell-db test lint type-check quality clean rebuild
.SILENT:

# ============================================================
# Configuration
# ============================================================

PROJECT_NAME := slea-ssem
DC := docker-compose

# Service names (from docker-compose.yml)
BACKEND := backend
DB := db

# 색상
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# ============================================================
# Help (Default Target)
# ============================================================

help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)$(PROJECT_NAME) - Docker 개발 환경$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(GREEN)초기 설정:$(NC)"
	@echo "  make init              🔧 .env 파일 초기화"
	@echo ""
	@echo "$(GREEN)Docker 관리:$(NC)"
	@echo "  make build             🔨 이미지 빌드 (Proxy 자동 주입)"
	@echo "  make up                🚀 서비스 시작"
	@echo "  make down              🛑 서비스 정지"
	@echo "  make restart           🔄 재시작"
	@echo "  make rebuild           🆕 clean + build + up"
	@echo ""
	@echo "$(GREEN)로깅 & 모니터링:$(NC)"
	@echo "  make logs              📊 Backend 로그"
	@echo "  make ps                📋 서비스 목록"
	@echo "  make shell             💻 Backend 셸"
	@echo "  make shell-db          💻 Database 셸"
	@echo ""
	@echo "$(GREEN)개발 (TDD):$(NC)"
	@echo "  make test              🧪 테스트 (pytest)"
	@echo "  make lint              🔎 코드 검사 (ruff)"
	@echo "  make type-check        ✅ 타입 검사 (mypy)"
	@echo "  make quality           📈 전체 검사 (lint + type-check + test)"
	@echo ""
	@echo "$(GREEN)정리:$(NC)"
	@echo "  make clean             🧹 캐시 삭제"
	@echo ""
	@echo "$(GREEN)사용 예시:$(NC)"
	@echo "  make init              # 1. 초기화"
	@echo "  make up                # 2. 시작"
	@echo "  make test              # 3. 테스트"
	@echo ""

# ============================================================
# 1. 초기 설정
# ============================================================

init:
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)🔧 .env 파일 생성 중...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✅ .env 생성 완료$(NC)"; \
	else \
		echo "$(BLUE)ℹ️  .env 파일이 이미 있습니다$(NC)"; \
	fi

# ============================================================
# 2. 빌드 (Proxy 자동 주입)
# ============================================================

build:
	@echo "$(YELLOW)🔨 이미지 빌드 중...$(NC)"
	@echo "$(BLUE)   - HTTP_PROXY: $${HTTP_PROXY:-[미설정]}$(NC)"
	@echo "$(BLUE)   - HTTPS_PROXY: $${HTTPS_PROXY:-[미설정]}$(NC)"
	@echo "$(BLUE)   - PIP_INDEX_URL: $${PIP_INDEX_URL:-[기본]}$(NC)"
	$(DC) build \
		--build-arg HTTP_PROXY=$${HTTP_PROXY} \
		--build-arg HTTPS_PROXY=$${HTTPS_PROXY} \
		--build-arg NO_PROXY=$${NO_PROXY} \
		--build-arg PIP_INDEX_URL=$${PIP_INDEX_URL}
	@echo "$(GREEN)✅ 빌드 완료$(NC)"

# ============================================================
# 3. 실행 및 관리
# ============================================================

up:
	@echo "$(YELLOW)🚀 서비스 시작 중...$(NC)"
	$(DC) up -d
	@sleep 2
	@$(DC) ps
	@echo ""
	@echo "$(GREEN)✅ 시작 완료!$(NC)"
	@echo "$(BLUE)포트:$(NC)"
	@echo "  - Backend: http://localhost:8000"
	@echo "  - Database: localhost:5432"

down:
	@echo "$(YELLOW)🛑 서비스 정지 중...$(NC)"
	$(DC) down
	@echo "$(GREEN)✅ 정지 완료$(NC)"

restart:
	@echo "$(YELLOW)🔄 서비스 재시작 중...$(NC)"
	$(DC) restart
	@echo "$(GREEN)✅ 재시작 완료$(NC)"

rebuild: down build up
	@echo "$(GREEN)✅ 재구축 완료$(NC)"

# ============================================================
# 4. 로깅 & 모니터링
# ============================================================

logs:
	@echo "$(YELLOW)📊 Backend 로그 (실시간)$(NC)"
	$(DC) logs -f $(BACKEND)

ps:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)실행 중인 서비스$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	$(DC) ps

# ============================================================
# 5. 컨테이너 접속
# ============================================================

shell:
	@echo "$(YELLOW)💻 Backend 셸 접속$(NC)"
	$(DC) exec $(BACKEND) bash

shell-db:
	@echo "$(YELLOW)💻 Database 접속$(NC)"
	$(DC) exec $(DB) psql -U slea_user -d sleassem_dev

# ============================================================
# 6. 개발 (TDD)
# ============================================================

test:
	@echo "$(YELLOW)🧪 테스트 실행 중...$(NC)"
	$(DC) exec $(BACKEND) pytest tests/backend/ -v --tb=short

lint:
	@echo "$(YELLOW)🔎 코드 검사 중 (Ruff)...$(NC)"
	$(DC) exec $(BACKEND) ruff check src tests

type-check:
	@echo "$(YELLOW)✅ 타입 검사 중 (mypy strict)...$(NC)"
	$(DC) exec $(BACKEND) mypy src --strict

quality: type-check lint test
	@echo "$(GREEN)✅ 품질 검사 완료$(NC)"

# ============================================================
# 7. 정리
# ============================================================

clean:
	@echo "$(YELLOW)🧹 캐시 파일 정리 중...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ 정리 완료$(NC)"

# ============================================================
# Default target
# ============================================================

.DEFAULT_GOAL := help
