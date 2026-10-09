"""Isolated local browser fixture; never point this app at a real database."""
import os
from importlib.resources import files
from uuid import uuid4

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import insert, select, func

from spg.api.admin import install_admin
from spg.api.authority import install_authority_boundary
from spg.config import Settings
from spg.infrastructure.persistence import Database, metadata


def create():
    if os.environ.get('SPG_DIAGNOSTIC_BROWSER_FIXTURE') != 'isolated-test-only':
        raise RuntimeError('Browser fixture requires its isolated test marker')
    settings = Settings(auth_mode='test-only-disabled')
    database = Database.from_settings(settings)
    with database.engine.begin() as connection:
        assert connection.scalar(select(func.count()).select_from(metadata.tables['product_works'])) == 0
        product_id, work_id = uuid4(), uuid4()
        connection.execute(insert(metadata.tables['software_products']).values(
            id=product_id, owner_id='human:owner', name='Browser fixture', lifecycle='ACTIVE'))
        connection.execute(insert(metadata.tables['product_works']).values(
            id=work_id, product_id=product_id, work_mode='LONG_LIVED_STEERING',
            raw_user_requirement='Browser fixture DESIGN Work',
            refined_title='Browser fixture DESIGN Work', condition='READY', constraints=[], tags=[]))
    app = FastAPI()
    install_authority_boundary(app, database=database, settings=settings)
    @app.get('/auth/session')
    def fixture_session():
        return {'actor_id':'human:owner'}
    install_admin(app, database, settings)
    app.mount('/assets', StaticFiles(directory=str(files('spg.web'))), name='assets')
    return app


app = create()
