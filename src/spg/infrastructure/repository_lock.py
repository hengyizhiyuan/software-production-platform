"""Cross-process exclusion for one repository/ref; PostgreSQL releases on crash."""
from contextlib import contextmanager
from hashlib import sha256
from sqlalchemy import text

@contextmanager
def repository_lock(database, repository_identity: str, repository_ref: str):
    key = int(sha256((repository_identity + "\0" + repository_ref).encode()).hexdigest()[:15], 16)
    with database.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
