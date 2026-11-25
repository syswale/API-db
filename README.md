# Containerized API + Database

FastAPI and PostgreSQL run with Docker Compose. A named volume keeps the data when containers are removed.

## Quick start

    cp .env.example .env     # set your own password in BOTH lines (letters and numbers only)
    docker compose up -d --build
    curl -s http://127.0.0.1:8000/health

Stop with `docker compose down` (keeps data) or `docker compose down -v` (deletes data).
