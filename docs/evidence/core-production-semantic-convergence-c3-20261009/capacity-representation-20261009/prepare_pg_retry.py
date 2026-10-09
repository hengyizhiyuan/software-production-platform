"""One proven controller configuration correction, preserving the first attempt."""
from pathlib import Path
HERE=Path(__file__).parent
text=(HERE/'qualify_capacity_pg.py').read_text(encoding='utf-8')
text=text.replace("TARGET=ROOT/'capacity-representation-20261009/owner-pg'", "TARGET=ROOT/'capacity-representation-20261009/owner-pg-retry-1'")
text=text.replace("NAME='watt-c3-capacity-owner-pg-20261010'", "NAME='watt-c3-capacity-owner-pg-retry-1-20261010'")
text=text.replace("container='watt-c3-capacity-owner-tests-20261010'", "container='watt-c3-capacity-owner-tests-retry-1-20261010'")
text=text.replace("database='spg_c3_capacity_fixture'", "database='c1_contract_continuity'")
with (HERE/'qualify_capacity_pg_retry.py').open('xb') as stream:stream.write(text.encode('utf-8'))
