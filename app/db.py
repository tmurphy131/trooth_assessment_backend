from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
import logging

logger = logging.getLogger("app.database")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trooth:trooth@localhost:5432/trooth_db")

# Enhanced engine configuration with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

async def check_database_health():
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database health check: PASSED")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check: FAILED - {str(e)}")
        return {"status": "unhealthy", "database": f"error: {str(e)}"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()