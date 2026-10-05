"""Read-only database fingerprint for a quiesced single-ECS recovery cut.

Run inside the existing runtime image. Never print row values or credentials.
A restored database must match every table before any owner resumes execution.
"""
import hashlib
import json
from sqlalchemy import text
from spg.config import Settings
from spg.infrastructure.persistence import Database


def snapshot():
    database = Database.from_settings(Settings())
    result = {}
    try:
        with database.engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
            with connection.begin():
                connection.execute(text('SET TRANSACTION READ ONLY'))
                names = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
                for name in names:
                    # Names come only from the database catalog and are quoted.
                    quoted = '"' + name.replace('"', '""') + '"'
                    rows = connection.execute(text('SELECT row_to_json(t)::text FROM ' + quoted + ' t ORDER BY row_to_json(t)::text')).scalars()
                    digest = hashlib.sha256()
                    count = 0
                    for row in rows:
                        digest.update(row.encode()); digest.update(b'\n'); count += 1
                    result[name] = {'rows': count, 'sha256': digest.hexdigest()}
    finally:
        database.dispose()
    return result


if __name__ == '__main__':
    print(json.dumps(snapshot(), sort_keys=True))
