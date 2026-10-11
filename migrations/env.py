from alembic import context
from sqlalchemy import create_engine, pool
from travelmate_api.config import get_settings
from travelmate_api.database import metadata, postgres_url

raw_url = get_settings().database_url
if not raw_url:
    raise RuntimeError("Set DATABASE_URL before running PostgreSQL migrations.")
url = postgres_url(raw_url)

if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
