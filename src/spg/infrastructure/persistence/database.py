"""SQLAlchemy engine, session factory, and PostgreSQL health composition."""

from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from spg.config import Settings
from spg.infrastructure.persistence.unit_of_work import UnitOfWork


class DatabaseConfigurationError(ValueError):
    """Raised when persistence is requested without usable PostgreSQL settings."""


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Non-authoritative PostgreSQL connectivity evidence."""

    database_name: str
    server_version_num: int


def configured_database_url(settings: Settings) -> URL:
    """Return the normalized synchronous PostgreSQL URL for infrastructure use."""

    if settings.database_url is None:
        raise DatabaseConfigurationError(
            "SPG_DATABASE_URL is required for persistence operations"
        )

    url = make_url(settings.database_url)
    if url.drivername == "postgresql":
        return url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        raise DatabaseConfigurationError(
            "SPG_DATABASE_URL must use PostgreSQL with the psycopg driver"
        )
    return url


@dataclass(frozen=True, slots=True)
class Database:
    """Owned SQLAlchemy resources with an explicit transaction entry point."""

    engine: Engine
    session_factory: sessionmaker[Session]

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        engine = create_engine(configured_database_url(settings), pool_pre_ping=True)
        factory = sessionmaker(
            bind=engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )
        return cls(engine=engine, session_factory=factory)

    def unit_of_work(self) -> UnitOfWork:
        """Return a fresh local transaction boundary."""

        return UnitOfWork(self.session_factory)

    def check(self) -> DatabaseHealth:
        """Verify PostgreSQL connectivity without mutating production state."""

        if self.engine.dialect.name != "postgresql":
            raise DatabaseConfigurationError("configured database is not PostgreSQL")

        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_database(), "
                    "current_setting('server_version_num')::integer"
                )
            ).one()

        return DatabaseHealth(database_name=row[0], server_version_num=row[1])

    def dispose(self) -> None:
        """Release pooled database connections owned by this composition."""

        self.engine.dispose()
