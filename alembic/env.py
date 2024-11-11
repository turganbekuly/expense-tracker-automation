# alembic/env.py

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.models.activation_code import Base  # Import Base from your models
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# This is the Alembic Config object, which provides access to the .ini file values.
config = context.config

# Set the database URL
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://username:password@localhost/dbname")
config.set_main_option("sqlalchemy.url", database_url)  # Ensures the URL is a string

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata
