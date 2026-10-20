from alembic import context
from sqlalchemy import text
from app.db import engine,Base
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=Base.metadata)
    with context.begin_transaction():
        if engine.dialect.name=='postgresql':connection.execute(text('SELECT pg_advisory_xact_lock(7263646373)'))
        context.run_migrations()
