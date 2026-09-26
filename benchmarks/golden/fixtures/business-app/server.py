"""Small existing application; source and schema are qualification fixtures."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
DATABASE = Path(os.environ.get("SITE_DATABASE_PATH", ROOT / "site.sqlite"))
FIELDS = {"users": ("name", "email", "status"),
    "customers": ("name", "email"), "orders": ("customer_id", "total", "status")}


def database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def migrate():
    with database() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            if connection.execute("SELECT name FROM schema_migrations WHERE name=?", (path.name,)).fetchone():
                continue
            connection.executescript(path.read_text())
            connection.execute("INSERT INTO schema_migrations VALUES (?)", (path.name,))


class Handler(BaseHTTPRequestHandler):
    def reply(self, value, status=200, content_type="application/json"):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            with database() as connection:
                connection.execute("SELECT 1").fetchone()
            return self.reply({"database": "available"})
        if path in {"/", "/users", "/customers", "/orders", "/help", "/about"}:
            return self.reply((ROOT / "web/index.html").read_bytes(), content_type="text/html; charset=utf-8")
        if path in {"/app.js", "/styles.css"}:
            return self.reply((ROOT / "web" / path[1:]).read_bytes(), content_type=(
                "text/javascript" if path.endswith("js") else "text/css"))
        parts = path.strip("/").split("/")
        if len(parts) in {2, 3} and parts[0] == "api" and parts[1] in FIELDS:
            table = parts[1]
            with database() as connection:
                if len(parts) == 2:
                    return self.reply([dict(row) for row in connection.execute(f"SELECT * FROM {table}")])
                row = connection.execute(f"SELECT * FROM {table} WHERE id=?", (parts[2],)).fetchone()
                return self.reply(dict(row) if row else {"error": "not found"}, 200 if row else 404)
        return self.reply({"error": "not found"}, 404)

    def do_POST(self):
        parts = urlsplit(self.path).path.strip("/").split("/")
        if len(parts) not in {2, 3} or parts[0] != "api" or parts[1] not in FIELDS:
            return self.reply({"error": "not found"}, 404)
        try:
            value = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            table = parts[1]
            if not isinstance(value, dict) or not value or set(value) - set(FIELDS[table]):
                return self.reply({"error": "invalid fields"}, 400)
            fields = tuple(value)
            with database() as connection:
                if len(parts) == 3:
                    connection.execute(f"UPDATE {table} SET " + ",".join(f"{key}=?" for key in fields)
                        + " WHERE id=?", (*value.values(), parts[2]))
                    identity = parts[2]
                else:
                    identity = connection.execute(f"INSERT INTO {table} (" + ",".join(fields)
                        + ") VALUES (" + ",".join("?" for _ in fields) + ")", tuple(value.values())).lastrowid
                row = connection.execute(f"SELECT * FROM {table} WHERE id=?", (identity,)).fetchone()
            return self.reply(dict(row), 201 if len(parts) == 2 else 200)
        except (ValueError, sqlite3.Error, TypeError):
            return self.reply({"error": "invalid request"}, 400)


if __name__ == "__main__":
    migrate()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("SITE_PORT", "8080"))), Handler).serve_forever()
