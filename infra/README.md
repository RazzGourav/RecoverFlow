# infra/

Infrastructure configuration files.

## Sub-directories

| Directory | Contents |
|---|---|
| `docker/` | Supplementary Docker configs (e.g., Postgres init scripts) |
| `ci/` | CI helper scripts and configs |
| `scripts/` | Operational scripts used in CI/CD |

Top-level Docker files (`docker-compose.yml`, `Dockerfile.*`) live at the repo root
so `docker compose up --build` works from the root without any path arguments.
