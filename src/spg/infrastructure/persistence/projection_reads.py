"""Exact, UoW-local read sets. Never installed by command stores.

Every adapter still constructs its canonical domain record and applies its own
conditions. Rows are loaded only for selected Work/runtime identities.
"""
def rows_for(session, table, filters, *, order=(), descending=False, ascending_ties=()):
    data = session.info.get('watt_projection_rows')
    if data is None or table.name not in data:
        return None
    rows = [row for row in data[table.name] if all(row[key] == value for key,value in filters.items())]
    if ascending_ties:
        rows = sorted(rows, key=lambda row: tuple(row[key] for key in ascending_ties))
    return sorted(rows, key=lambda row: tuple((row[key] is None, row[key] if row[key] is not None else 0) for key in order), reverse=descending) if order else rows


def first_for(session, table, filters, **kwargs):
    rows = rows_for(session, table, filters, **kwargs)
    return None if rows is None else (rows[0] if rows else {})
