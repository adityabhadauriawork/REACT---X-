import logging
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateIndex

logger = logging.getLogger("sih26162.migrations")

def run_auto_migrations(engine, Base):
    """
    Idempotent schema migration utility.
    Compares SQLAlchemy Base metadata with the live database schema (SQLite or PostgreSQL),
    adds any missing columns, and creates any missing indexes while strictly preserving
    all existing reference and operational data.
    """
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    dialect_name = engine.dialect.name

    logger.info(f"Running automated schema verification on '{dialect_name}' database...")
    migrated_columns_count = 0
    migrated_indexes_count = 0

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in db_tables:
                # Table does not exist, create it cleanly
                logger.info(f"Creating missing table '{table_name}'...")
                table.create(bind=conn, checkfirst=True)
                continue

            # Fetch existing columns in DB
            db_cols = {col["name"]: col for col in inspector.get_columns(table_name)}
            
            for col_name, col in table.columns.items():
                if col_name not in db_cols:
                    col_type = col.type.compile(engine.dialect)
                    # For SQLite, boolean and json are typically represented as BOOLEAN/JSON/TEXT
                    alter_query = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}'
                    logger.info(f"Applying schema migration: {alter_query}")
                    conn.execute(text(alter_query))
                    migrated_columns_count += 1

            # Fetch existing indexes
            try:
                db_indexes = {idx["name"] for idx in inspector.get_indexes(table_name) if idx.get("name")}
                for index in table.indexes:
                    if index.name and index.name not in db_indexes:
                        logger.info(f"Creating missing index '{index.name}' on '{table_name}'...")
                        conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{index.name}" ON "{table_name}" ({", ".join(c.name for c in index.columns)})'))
                        migrated_indexes_count += 1
            except Exception as e:
                logger.warning(f"Index verification skipped for '{table_name}': {e}")

    logger.info(f"Schema migration completed: {migrated_columns_count} column(s) added, {migrated_indexes_count} index(es) verified.")
    return {
        "migrated_columns": migrated_columns_count,
        "migrated_indexes": migrated_indexes_count
    }

if __name__ == "__main__":
    import sys, pkgutil, importlib
    sys.path.insert(0, ".")
    import app.models
    for _, module_name, _ in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module_name}")
    from app.core.database import engine, Base
    result = run_auto_migrations(engine, Base)
    print("Migration result:", result)
