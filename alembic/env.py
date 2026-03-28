from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Bu satırları ekle - Modellerimizi import et
from app.shared.database import Base
from app.core.config import settings
# Tüm modelleri import et (Alembic metadata'yı görebilsin)
from app.users.models import User
from app.books.models import Book

# this is the Alembic Config object
config = context.config

# Önce ENV'deki DATABASE_URL'e bak, yoksa settings'ten al
database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL

# DEBUG için istersen bir kere loglayabilirsin (deploy'dan sonra silebilirsin)
print(f"[Alembic] Using DATABASE_URL: {database_url}")

# Database URL'i settings'ten al (env.py yerine)
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata
"""
target_metadata nedir?
- Alembic'in modellerimizi görmesi için
- Base.metadata → Tüm modellerin metadata'sını içerir
- autogenerate bu metadata'yı kullanır
"""

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()