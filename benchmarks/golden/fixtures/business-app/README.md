# Small operations site

This fixture is a runnable existing site, with real SQLite persistence and an
HTTP API. Run `python server.py`, then open port 8080. Database migrations are
applied on startup. The initial user, order and customer records are fixture
data; they must not be presented as real company facts.

Existing routes: `/`, `/users`, `/customers`, `/orders`, `/help`, `/about`.
Existing API collections: `/api/users`, `/api/customers`, `/api/orders`.
The user schema already includes `status`; the customer schema includes name
and email. There are no customer notes, feedback records or CRM workflows.
The site has two login buttons with different locations and purposes.

The login controls are existing UI affordances; authentication is not implemented.
This fixture does not connect to external accounts or production data.
