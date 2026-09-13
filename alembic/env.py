"""Alembic migration runtime configuration.

Configures database connectivity, logging, and metadata targets for
executing schema migrations in both offline and online modes.
"""

import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure the backend directory is in the module search path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import Base
# Register all SQLAlchemy models with Base.metadata for autogenerate detection
from app.models.lead import Lead  # noqa: F401
from app.models.dedupe import DedupeCandidate  # noqa: F401
from app.models.form_submission import FormSubmission  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Dynamic database URL from settings
settings = get_settings()
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Escape % as %% for configparser interpolation safety
safe_url = db_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", safe_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from app.database import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
