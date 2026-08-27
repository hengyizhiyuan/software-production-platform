import os

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, delete, text

from spg.config import Settings
from spg.infrastructure.persistence import Database


test_metadata = MetaData()
versioned_records = Table(
    "spg_s1b_test_versioned_records",
    test_metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("value", String(200), nullable=False),
    Column("version", Integer, nullable=False, server_default=text("0")),
)


@pytest.fixture(scope="session")
def postgres_database() -> Database:
    database_url = os.environ.get("SPG_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SPG_TEST_DATABASE_URL is required for real PostgreSQL tests")

    database = Database.from_settings(Settings(database_url=database_url))
    database.check()
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture(scope="session")
def versioned_table(postgres_database: Database):
    with postgres_database.engine.begin() as connection:
        versioned_records.drop(connection, checkfirst=True)
        versioned_records.create(connection)
    try:
        yield versioned_records
    finally:
        with postgres_database.engine.begin() as connection:
            versioned_records.drop(connection, checkfirst=True)


@pytest.fixture(autouse=True)
def clean_test_only_table(postgres_database: Database, versioned_table) -> None:
    with postgres_database.engine.begin() as connection:
        connection.execute(delete(versioned_table))
