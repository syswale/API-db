# Containerized API + database

A FastAPI service and PostgreSQL run with Docker Compose. The goal was to prove the app can restart, and even be rebuilt from scratch, without losing data.

## What was built

| Piece | Detail |
|---|---|
| API | FastAPI with `GET /health`, `POST /items` (returns 201) and `GET /items` |
| Database | `postgres:16`, reached from the API at the Compose hostname `db` |
| Image | Multi-stage `Dockerfile`: dependencies are installed in a builder stage, and only the installed packages and `main.py` are copied into the final image |
| User | The service runs as non-root `appuser` (UID 10001) |
| Persistence | Named volume `pgdata` mounted at `/var/lib/postgresql/data` |
| Health checks | `db` uses `pg_isready`; `api` calls its own `/health`, which runs `SELECT 1` against the database |
| Start order | `depends_on` with `condition: service_healthy`, so the API starts after the database is healthy |
| Exposure | The API is published on `127.0.0.1:8000` only. Postgres is not published to the host |

Design choice: the app opens a **new database connection for every request** and turns a database outage into `503 database unavailable` instead of crashing.

## Verification

```bash
docker compose up -d --build
docker compose ps                         # api and db both healthy
docker compose exec api id                # should show uid=10001(appuser)
docker compose exec api python -c "import socket; print(socket.gethostbyname('db'))"
docker volume ls                          # api-db-lab_pgdata
```

Observed: both services `healthy`, the name `db` resolved to `172.18.0.2` on the Compose network, and the volume `api-db-lab_pgdata` existed.

## Persistence proof

1. Created a record: `POST /items` with `{"name":"survivor"}` returned `{"id":1,"name":"survivor"}`.
2. Ran `docker compose down`. This removed both containers and the network. `docker volume ls` still listed `api-db-lab_pgdata`.
3. Ran `docker compose up -d`. `db` came back `Healthy`.
4. `GET /items` returned `[{"id":1,"name":"survivor"}]`.

The containers were brand new, so the only place the record could have survived is the **named volume**. `down` keeps volumes; `down -v` would delete them.

## Failure task: database stopped

**Break:** `docker compose stop db`.

**Observation**
- `GET /health` and `GET /items` returned `503` with `database unavailable`. The API did not crash.
- `docker compose exec api python -c "...gethostbyname('db')..."` failed with `socket.gaierror: [Errno -2] Name or service not known`.
- `docker compose ps` showed `api` as `Up ... (unhealthy)`, and the API log showed a `GET /health ... 503` every 10 seconds (the health check). The stopped `db` container was hidden from `ps`; `docker compose ps -a` shows it.

**Cause:** a stopped container drops out of Compose's internal DNS, so the API's lookup of `db` failed. This is a DNS-style failure, not a refused connection. The database was down, and the API reported it cleanly.

**Restore:** `docker compose start db`, with no API restart.

**Result**
- `db` became `healthy` within seconds, and `api` returned to `healthy` on its own. Its uptime (29 minutes) showed it was never restarted, while `db` showed `Up 17 seconds`.
- The name `db` resolved again (`172.18.0.2`).
- `GET /items` returned 200 with `[{"id":1,"name":"survivor"}]`.

**Does the API retry or need a restart?** It recovers by itself. Each request opens a fresh connection, so as soon as the database is reachable again, requests succeed. An app that kept one long-lived connection from startup would hold a dead connection and need reconnect logic or a restart. A connection pool with health checks is the production version of this.

## Lessons

- `docker compose ps` hides stopped containers. Use `ps -a`.
- `unhealthy` is a status, not an action. Docker does not restart a container just because its health check fails.
- Code is baked into the image at build time. Changing `main.py` needs `docker compose up -d --build`; `restart` reuses the old image.
- YAML indentation is structure: a mis-indented `build:` or `volumes:` produced schema errors from `docker compose config`.
- Windows line endings (`^M`) can end up in files created from pasted text. `cat -A` shows them, and `sed -i 's/\r$//' file` removes them.
- `docker compose config --quiet` validates a Compose file before anything is started.


## Cleanup

```bash
docker compose down        # stop and remove containers; keep the data
docker compose down -v     # also delete the pgdata volume (data is lost)
```
