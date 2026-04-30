# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChatGPT2API is a reverse-engineered proxy for ChatGPT's web image generation/editing APIs, exposing OpenAI-compatible endpoints (`/v1/images/generations`, `/v1/images/edits`, `/v1/chat/completions`, `/v1/responses`, `/v1/messages`). It manages an account pool with automatic token rotation and provides a built-in web UI for drawing.

## Tech Stack

- **Backend**: Python 3.13+, FastAPI, uvicorn, curl-cffi (for impersonating browser requests to ChatGPT), Pillow, tiktoken
- **Frontend**: Next.js 16, React 19, Tailwind CSS 4, Zustand (state), Radix UI (components)
- **Package manager**: uv (backend), npm (frontend)
- **Deployment**: Docker (multi-arch: amd64/arm64)

## Development Commands

```bash
# Install Python dependencies
uv sync

# Run backend locally (port 8000)
uv run uvicorn main:app --reload --port 8000

# Run frontend dev server (in web/ directory)
cd web && npm install && npm run dev

# Run tests (requires running backend on port 8000)
uv run python -m pytest test/
uv run python -m unittest test.test_v1_models

# Docker (full stack)
docker compose up -d
```

## Architecture

```
api/             # FastAPI route handlers (thin layer, delegates to services)
  app.py         # create_app() factory, lifespan management, CORS, static files
  ai.py          # /v1/images/*, /v1/chat/completions, /v1/responses, /v1/messages routes
  accounts.py    # Account pool CRUD endpoints
  support.py     # Auth middleware (require_identity), image URL resolution

services/        # Business logic
  config.py      # ConfigStore singleton (config.json + env vars), storage backend factory
  account_service.py   # Account pool management, token rotation, rate-limit handling
  openai_backend_api.py  # Low-level ChatGPT web backend client (curl-cffi, PoW, Turnstile)
  auth_service.py      # API key authentication
  storage/       # Pluggable storage backends
    base.py      # StorageBackend ABC
    json_storage.py, database_storage.py, git_storage.py  # Implementations
    factory.py   # create_storage_backend() - selects backend via STORAGE_BACKEND env var
  protocol/      # Request/response format adapters
    openai_v1_image_generations.py, openai_v1_chat_complete.py, etc.
  register/      # Account registration flows
    openai_register.py, mail_provider.py

utils/           # Shared utilities
  helper.py      # SSE parsing, UUID generation, token anonymization
  pow.py         # Proof-of-Work token generation for ChatGPT sentinel
  turnstile.py   # Cloudflare Turnstile CAPTCHA solving

web/             # Next.js frontend (image drawing workspace + account management UI)
test/            # Tests (unittest-based, some require live backend)
```

## Key Patterns

- **Auth**: All API requests require `Authorization: Bearer <auth-key>`. The auth key comes from `config.json` or `CHATGPT2API_AUTH_KEY` env var.
- **Config**: `config.json` is the primary config file (not committed to git). Env vars override config.json values.
- **Storage backends**: Controlled by `STORAGE_BACKEND` env var (`json` | `sqlite` | `postgres` | `git`). The `StorageBackend` ABC in `services/storage/base.py` defines the interface.
- **Account pool**: Accounts are stored via the storage backend. The `AccountService` handles round-robin selection, automatic refresh, and removal of invalid/rate-limited accounts.
- **ChatGPT backend**: `OpenAIBackendAPI` in `services/openai_backend_api.py` handles all communication with chatgpt.com, including PoW challenges and Turnstile CAPTCHA.
- **Protocol adapters**: `services/protocol/` contains separate modules for each OpenAI-compatible endpoint, translating between the OpenAI format and ChatGPT's internal format.

## Testing

Tests are in `test/` and use `unittest`. Some tests (`test_v1_models.py`, `test_generations.py`) require a running backend instance on `localhost:8000` and valid credentials in `config.json`. Unit-style tests like `test_image_task_service.py` and `test_config.py` can run standalone.

## Environment Variables

Key env vars (see `.env.example` for full list):
- `CHATGPT2API_AUTH_KEY` - API auth key (overrides config.json)
- `STORAGE_BACKEND` - `json` | `sqlite` | `postgres` | `git`
- `DATABASE_URL` - Connection string for sqlite/postgres backends
- `GIT_REPO_URL`, `GIT_TOKEN` - For git storage backend
- `CHATGPT2API_BASE_URL` - Base URL for generated image URLs
