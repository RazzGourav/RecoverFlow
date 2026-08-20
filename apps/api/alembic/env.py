"""
Alembic migration environment.

Why this file exists:
  Alembic needs to know:
  1. Where the database is (loaded from DATABASE_SYNC_URL env var — never
     hardcoded in this file).
  2. Which SQLAlchemy metadata to use for autogenerate support.

  We import `Base` from db.models so that `alembic revision --autogenerate`
  can detect schema diffs automatically in future phases.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make the API package importable from this file's working directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import models so that Base.metadata knows about all tables.
# This import must come AFTER sys.path is adjusted.
from db.models import Base  # noqa: E402
from config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object (provides access to alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Inject the database URL from environment — never from alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_sync_url)

# Set up Python logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object for autogenerate support.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """
    Run migrations without a DB connection ('offline' mode).

    Useful for generating a SQL script to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode (applies migrations against a live DB)
# ---------------------------------------------------------------------------


def run_migrations_online() -> None:
    """
    Run migrations with a live DB connection ('online' mode).

    This is what `alembic upgrade head` calls in the Docker entrypoint.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no connection pooling in migration scripts
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
