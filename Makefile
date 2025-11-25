# ============================================================
# SLEA-SSEM Makefile
# Docker 및 개발 환경 관리
# 사외(공개) + 사내(폐쇄) 환경 모두 지원
# ============================================================

SHELL := /bin/bash
.ONESHELL:
.PHONY: help init build up down logs ps shell test format lint migrate sync clean rebuild
.SILENT:

# ============================================================
# Variables
# ============================================================

# 프로젝트 정보
PROJECT_NAME ?= slea-ssem
APP_NAME ?= slea-backend
DB_NAME ?= slea-db

# Docker 이미지
IMAGE ?= $(APP_NAME)
TAG ?= 0.1.0

# 환경 선택 (사외: default, 사내: company)
ENVIRONMENT ?= default

# 포트
BACKEND_PORT ?= 8000
DB_PORT ?= 5432

# 색상 정의
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# ============================================================
# Help
# ============================================================

help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)$(PROJECT_NAME) - Docker 개발 환경 관리$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(GREEN)초기 설정:$(NC)"
	@echo "  make init              🔧 환경 파일 초기화"
	@echo ""
	@echo "$(GREEN)Docker 관리:$(NC)"
	@echo "  make build             🔨 이미지 빌드"
	@echo "  make up                🚀 환경 시작"
	@echo "  make down              🛑 환경 정지"
	@echo "  make restart           🔄 환경 재시작"
	@echo "  make rebuild           🔄 빌드 + 시작 (fresh)"
	@echo ""
	@echo "$(GREEN)로깅 & 모니터링:$(NC)"
	@echo "  make logs              📊 실시간 로그"
	@echo "  make ps                📋 실행 중인 서비스 목록"
	@echo "  make shell             💻 Backend 컨테이너 셸"
	@echo "  make shell-db          💻 DB 컨테이너 셸"
	@echo ""
	@echo "$(GREEN)개발 작업:$(NC)"
	@echo "  make test              🧪 테스트 실행"
	@echo "  make test-watch        🔍 테스트 감시 모드"
	@echo "  make format            📝 코드 포맷팅"
	@echo "  make lint              🔎 코드 검사"
	@echo "  make type-check        ✅ 타입 검사"
	@echo ""
	@echo "$(GREEN)데이터베이스:$(NC)"
	@echo "  make migrate           🗄️  마이그레이션 실행"
	@echo "  make migration-new MSG='message'  새 마이그레이션 생성"
	@echo "  make db-reset          🔄 DB 초기화 (위험!)"
	@echo ""
	@echo "$(GREEN)Git & 동기화:$(NC)"
	@echo "  make sync              🔄 Upstream 동기화"
	@echo "  make status            📊 Git 상태"
	@echo ""
	@echo "$(GREEN)정리:$(NC)"
	@echo "  make clean             🧹 미사용 리소스 삭제"
	@echo "  make clean-all         🧹 모든 데이터 삭제 (위험!)"
	@echo ""
	@echo "$(GREEN)옵션:$(NC)"
	@echo "  ENVIRONMENT=company    사내 환경 사용"
	@echo "  BACKEND_PORT=8000      Backend 포트 지정"
	@echo "  DB_PORT=5432           DB 포트 지정"
	@echo ""
	@echo "$(GREEN)예시:$(NC)"
	@echo "  make up                # 사외 개발 환경 시작"
	@echo "  make up ENVIRONMENT=company  # 사내 환경 시작"
	@echo "  make test              # 테스트 실행"
	@echo "  make sync              # Upstream 동기화"
	@echo ""

# ============================================================
# 초기 설정
# ============================================================

init:
	@echo "$(YELLOW)🔧 초기 설정 시작...$(NC)"
	@if [ "$(ENVIRONMENT)" = "company" ]; then \
		if [ ! -f docker-compose.override.yml ]; then \
			echo "$(YELLOW)  → docker-compose.override.yml 생성 중...$(NC)"; \
			cp docker-compose.override.yml.example docker-compose.override.yml 2>/dev/null || echo "$(RED)  ⚠️  docker-compose.override.yml.example이 없습니다$(NC)"; \
		fi; \
		if [ ! -f .env.company ]; then \
			echo "$(YELLOW)  → .env.company 생성 필요 (회사 정보 입력)$(NC)"; \
		fi; \
	else \
		if [ ! -f .env ]; then \
			echo "$(YELLOW)  → .env 파일 생성 중...$(NC)"; \
			cp .env.example .env 2>/dev/null || echo "$(BLUE)  ℹ️  .env.example이 없습니다. 수동으로 .env를 생성하세요$(NC)"; \
		fi; \
	fi
	@echo "$(GREEN)✅ 초기 설정 완료$(NC)"

# ============================================================
# Docker 관리
# ============================================================

build:
	@echo "$(YELLOW)🔨 Docker 이미지 빌드 중: $(IMAGE):$(TAG)$(NC)"
	docker build \
		--build-arg HTTP_PROXY=$(HTTP_PROXY) \
		--build-arg HTTPS_PROXY=$(HTTPS_PROXY) \
		--build-arg NO_PROXY=$(NO_PROXY) \
		--build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) \
		--build-arg PIP_EXTRA_INDEX_URL=$(PIP_EXTRA_INDEX_URL) \
		-t $(IMAGE):$(TAG) \
		-t $(IMAGE):latest .
	@echo "$(GREEN)✅ 빌드 완료: $(IMAGE):$(TAG)$(NC)"

up:
	@echo "$(YELLOW)🚀 환경 시작 중 ($(ENVIRONMENT))...$(NC)"
	docker-compose up -d
	@sleep 2
	@echo ""
	@echo "$(GREEN)✅ 시작 완료!$(NC)"
	@echo ""
	@echo "$(BLUE)포트:$(NC)"
	@echo "  Backend:  http://localhost:$(BACKEND_PORT)"
	@echo "  Database: localhost:$(DB_PORT)"
	@echo ""
	@echo "$(BLUE)다음 명령을 실행하세요:$(NC)"
	@echo "  make logs      # 로그 확인"
	@echo "  make test      # 테스트 실행"
	@echo "  make shell     # Backend 셸"

down:
	@echo "$(YELLOW)🛑 환경 정지 중...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ 정지 완료$(NC)"

restart:
	@echo "$(YELLOW)🔄 환경 재시작 중...$(NC)"
	docker-compose restart
	@sleep 2
	@echo "$(GREEN)✅ 재시작 완료$(NC)"

rebuild: down build up
	@echo "$(GREEN)✅ 재구축 완료 (fresh)$(NC)"

# ============================================================
# 로깅 & 모니터링
# ============================================================

logs:
	@echo "$(YELLOW)📊 실시간 로그 (Backend)$(NC)"
	docker-compose logs -f backend

logs-db:
	@echo "$(YELLOW)📊 실시간 로그 (Database)$(NC)"
	docker-compose logs -f db

logs-all:
	@echo "$(YELLOW)📊 실시간 로그 (모든 서비스)$(NC)"
	docker-compose logs -f

ps:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)실행 중인 서비스$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@docker-compose ps
	@echo ""

# ============================================================
# 컨테이너 접속
# ============================================================

shell:
	@echo "$(YELLOW)💻 Backend 컨테이너 셸 접속$(NC)"
	docker-compose exec backend bash

shell-db:
	@echo "$(YELLOW)💻 Database 컨테이너 접속$(NC)"
	docker-compose exec db psql -U slea_user -d sleassem_dev

# ============================================================
# 개발 작업
# ============================================================

test:
	@echo "$(YELLOW)🧪 테스트 실행 중 (Backend)$(NC)"
	docker-compose exec backend pytest tests/backend/ -v --tb=short

test-watch:
	@echo "$(YELLOW)🔍 테스트 감시 모드 (변경사항 자동 감지)$(NC)"
	docker-compose exec backend pytest tests/backend/ -v --tb=short -W ignore::DeprecationWarning --forked -x -s

test-coverage:
	@echo "$(YELLOW)📊 테스트 커버리지 분석 중$(NC)"
	docker-compose exec backend pytest tests/backend/ --cov=src --cov-report=html
	@echo "$(GREEN)✅ 커버리지 리포트: htmlcov/index.html$(NC)"

lint:
	@echo "$(YELLOW)🔎 코드 검사 중 (Ruff)$(NC)"
	docker-compose exec backend ruff check src tests

format:
	@echo "$(YELLOW)📝 코드 포맷팅 중 (Black + isort)$(NC)"
	docker-compose exec backend bash -c "black src tests && isort src tests"

type-check:
	@echo "$(YELLOW)✅ 타입 검사 중 (mypy strict)$(NC)"
	docker-compose exec backend mypy src --strict

quality:
	@echo "$(YELLOW)🔍 코드 품질 검사 (lint + format + type-check)$(NC)"
	@echo "$(BLUE)→ Lint 검사...$(NC)"
	@$(MAKE) lint
	@echo "$(BLUE)→ 타입 검사...$(NC)"
	@$(MAKE) type-check
	@echo "$(GREEN)✅ 품질 검사 완료$(NC)"

# ============================================================
# 데이터베이스
# ============================================================

migrate:
	@echo "$(YELLOW)🗄️  마이그레이션 실행 중...$(NC)"
	docker-compose exec backend alembic upgrade head
	@echo "$(GREEN)✅ 마이그레이션 완료$(NC)"

migration-new:
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ MSG 변수를 지정하세요: make migration-new MSG='add user table'$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📝 새 마이그레이션 생성: $(MSG)$(NC)"
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✅ 마이그레이션 파일 생성 완료 (alembic/versions/)$(NC)"

migration-history:
	@echo "$(BLUE)마이그레이션 이력:$(NC)"
	docker-compose exec backend alembic history --verbose

db-reset:
	@echo "$(RED)⚠️  주의: 모든 데이터가 삭제됩니다!$(NC)"
	@read -p "정말 초기화하시겠습니까? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(YELLOW)🔄 DB 초기화 중...$(NC)"; \
		docker-compose down -v; \
		docker-compose up -d db; \
		sleep 5; \
		docker-compose exec backend alembic upgrade head; \
		echo "$(GREEN)✅ DB 초기화 완료$(NC)"; \
	else \
		echo "$(YELLOW)취소됨$(NC)"; \
	fi

# ============================================================
# Git & 동기화
# ============================================================

sync:
	@echo "$(YELLOW)🔄 Upstream 동기화 중...$(NC)"
	@if [ -f tools/sync-with-upstream.sh ]; then \
		bash tools/sync-with-upstream.sh; \
	else \
		echo "$(RED)❌ tools/sync-with-upstream.sh를 찾을 수 없습니다$(NC)"; \
	fi

status:
	@echo "$(BLUE)📊 Git 상태:$(NC)"
	git status --short
	@echo ""
	@echo "$(BLUE)📌 최근 커밋:$(NC)"
	git log --oneline -5

# ============================================================
# 정리
# ============================================================

clean:
	@echo "$(YELLOW)🧹 미사용 Docker 리소스 정리 중...$(NC)"
	docker system prune -f --volumes
	@echo "$(GREEN)✅ 정리 완료$(NC)"

clean-all:
	@echo "$(RED)⚠️  주의: 모든 컨테이너, 볼륨, 이미지가 삭제됩니다!$(NC)"
	@read -p "정말 진행하시겠습니까? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(YELLOW)🧹 전체 정리 중...$(NC)"; \
		docker-compose down -v; \
		docker system prune -a -f --volumes; \
		echo "$(GREEN)✅ 전체 정리 완료$(NC)"; \
	else \
		echo "$(YELLOW)취소됨$(NC)"; \
	fi

# ============================================================
# 유틸리티
# ============================================================

info:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)프로젝트 정보$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)프로젝트:$(NC) $(PROJECT_NAME)"
	@echo "$(GREEN)이미지:$(NC) $(IMAGE):$(TAG)"
	@echo "$(GREEN)환경:$(NC) $(ENVIRONMENT)"
	@echo "$(GREEN)Backend 포트:$(NC) $(BACKEND_PORT)"
	@echo "$(GREEN)DB 포트:$(NC) $(DB_PORT)"
	@echo ""
	@docker --version
	@docker compose version

version:
	@echo "$(PROJECT_NAME) v$(TAG)"

# ============================================================
# 전체 정리 / 상태 확인
# ============================================================

health:
	@echo "$(YELLOW)🏥 시스템 상태 확인 중...$(NC)"
	@echo ""
	@echo "$(BLUE)Docker:$(NC)"
	@docker version --format '{{ .Server.Version }}' 2>/dev/null && echo "  ✅ Docker running" || echo "  ❌ Docker not available"
	@echo ""
	@echo "$(BLUE)Services:$(NC)"
	@docker-compose ps 2>/dev/null | grep -E "slea-db|slea-backend" | while read line; do echo "  $$line"; done
	@echo ""
	@echo "$(BLUE)Network:$(NC)"
	@curl -s http://localhost:$(BACKEND_PORT)/api/health > /dev/null && echo "  ✅ Backend responding" || echo "  ⚠️  Backend not responding"
	@echo ""

# ============================================================
# 문서 & 도움말
# ============================================================

docs:
	@echo "$(BLUE)📚 관련 문서:$(NC)"
	@echo "  · QUICKSTART-OUTSIDE-IN.md     (5분 시작 가이드)"
	@echo "  · OUTSIDE-IN-STRATEGY.md       (전략 상세 설명)"
	@echo "  · DOCKER-DEVELOPMENT-GUIDE.md  (Docker 완전 가이드)"
	@echo "  · IMPLEMENTATION-CHECKLIST.md  (구현 로드맵)"
	@echo ""
	@echo "$(BLUE)명령어:$(NC)"
	@echo "  make help          이 도움말 보기"
	@echo "  make info          프로젝트 정보 확인"
	@echo "  make health        시스템 상태 확인"
	@echo "  make docs          문서 안내"

.DEFAULT_GOAL := help
