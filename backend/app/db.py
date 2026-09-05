from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.models import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _install_immutability_trigger(eng):
    dialect = eng.dialect.name
    with eng.begin() as conn:
        if dialect == "sqlite":
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS decisions_no_update
                BEFORE UPDATE ON decisions
                BEGIN
                    SELECT RAISE(ABORT, 'decisions ledger is append-only: UPDATE/DELETE blocked');
                END;
            """))
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS decisions_no_delete
                BEFORE DELETE ON decisions
                BEGIN
                    SELECT RAISE(ABORT, 'decisions ledger is append-only: UPDATE/DELETE blocked');
                END;
            """))
        elif dialect == "postgresql":
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION decisions_block_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'decisions ledger is append-only: UPDATE/DELETE blocked';
                END;
                $$ LANGUAGE plpgsql;
            """))
            conn.execute(text("""
                DROP TRIGGER IF EXISTS decisions_no_mutation ON decisions;
            """))
            conn.execute(text("""
                CREATE TRIGGER decisions_no_mutation
                BEFORE UPDATE OR DELETE ON decisions
                FOR EACH ROW EXECUTE FUNCTION decisions_block_mutation();
            """))


def init_db(eng=None):
    eng = eng or engine
    Base.metadata.create_all(eng)
    _install_immutability_trigger(eng)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()