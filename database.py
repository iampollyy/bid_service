import logging
import urllib
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_DATABASE};"
    f"UID={DB_USERNAME};"
    f"PWD={DB_PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
)

DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

SCHEMA = "BidSchema_Polina"

logger.info("Creating database engine for server=%s db=%s", DB_SERVER, DB_DATABASE)
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    logger.debug("Opening new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")


def create_schema():
    logger.info("Ensuring schema '%s' exists", SCHEMA)
    with engine.connect() as conn:
        conn.execute(text(
            f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{SCHEMA}') "
            f"EXEC('CREATE SCHEMA [{SCHEMA}]')"
        ))
        conn.commit()
    logger.info("Schema check complete")