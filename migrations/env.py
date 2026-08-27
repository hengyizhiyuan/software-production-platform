"""Alembic environment using the governed SPG settings boundary."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from spg.config import Settings
from spg.infrastructure.persistence import configured_database_url, metadata


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def configured_url() -> str:
    """Read the migration URL from environment-backed typed Settings."""

    url = configured_database_url(Settings())
    return url.render_as_string(hide_password=False).replace("%", "%%")


def run_migrations_offline() -> None:
    context.configure(
        url=configured_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = configured_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
