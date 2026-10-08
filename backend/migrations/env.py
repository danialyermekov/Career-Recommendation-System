from alembic import context
import sqlalchemy as sa
from database import get_engine, metadata

def configure(connection=None):
    context.configure(connection=connection, dialect_name='postgresql', target_metadata=metadata,
        include_schemas=True, version_table_schema='careerflow', literal_binds=connection is None)
    with context.begin_transaction():
        if connection is None:
            context.execute('CREATE SCHEMA IF NOT EXISTS careerflow')
        context.run_migrations()

if context.is_offline_mode():
    configure()
else:
    with get_engine().begin() as connection:
        connection.execute(sa.text('SELECT pg_advisory_xact_lock(17290511)'))
        connection.execute(sa.text('CREATE SCHEMA IF NOT EXISTS careerflow'))
        configure(connection)
