from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
import logging

logger = logging.getLogger("app.database")

# Primary config: allow DATABASE_URL to be set, or configure CLOUD_SQL_INSTANCE
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trooth:trooth@localhost:5432/trooth_db")
CLOUD_SQL_INSTANCE = os.getenv("CLOUD_SQL_INSTANCE")  # e.g. project:region:instance


def _create_engine_with_connector():
    """Attempt to create a SQLAlchemy engine using the Cloud SQL Python Connector.
    Falls back (raises) if the connector is not available or the instance is not set.
    """
    try:
        # Import here so the package is optional unless CLOUD_SQL_INSTANCE is used
        from google.cloud.sql.connector import Connector, IPTypes
        import pg8000
    except Exception as e:
        raise RuntimeError(
            "Cloud SQL Python connector is not installed or failed to import: " + str(e)
        )

    if not CLOUD_SQL_INSTANCE:
        raise RuntimeError("CLOUD_SQL_INSTANCE environment variable is not set")

    connector = Connector()

    # Allow IAM-based DB authentication (short-lived IAM DB tokens) when requested.
    CLOUD_SQL_IAM_AUTH = os.getenv("CLOUD_SQL_IAM_AUTH", "false").lower() == "true"

    def getconn():
        # When using IAM auth, the connector will create and use an ephemeral auth token
        # for the Postgres user. In that case we do not provide a password; the connector
        # will handle passing the token to the DB driver. Use the psycopg2 driver for IAM.
        connect_kwargs = {
            "ip_type": IPTypes.PRIVATE if os.getenv("CLOUD_SQL_USE_PRIVATE_IP", "false").lower() == "true" else IPTypes.PUBLIC,
            "user": os.getenv("DB_USER", "trooth"),
            "db": os.getenv("DB_NAME", "trooth_db"),
        }
        if CLOUD_SQL_IAM_AUTH:
            connect_kwargs["enable_iam_auth"] = True
            driver = "psycopg2"
        else:
            connect_kwargs["password"] = os.getenv("DB_PASS", "trooth")
            driver = "pg8000"

        # Try the normal connector IAM flow first.
        try:
            conn = connector.connect(CLOUD_SQL_INSTANCE, driver, **connect_kwargs)
            return conn
        except Exception as e:
            logger.warning("Connector IAM direct connect failed: %s", e)

        # Fallback: try to obtain an OAuth access token from ADC and pass it as the password
        # (pg8000 expects bytes) — this can work with IAM DB auth where the token is accepted
        # as a temporary password by the server.
        if CLOUD_SQL_IAM_AUTH:
            try:
                import google.auth
                from google.auth.transport.requests import Request as GoogleRequest

                creds, _ = google.auth.default()
                creds.refresh(GoogleRequest())
                token = creds.token
                if token is None:
                    raise RuntimeError("ADC returned no access token")

                connect_kwargs_fallback = connect_kwargs.copy()
                # pg8000 expects password as bytes
                connect_kwargs_fallback["password"] = token.encode("utf8")
                # disable enable_iam_auth to avoid duplicate flows
                connect_kwargs_fallback.pop("enable_iam_auth", None)

                conn = connector.connect(CLOUD_SQL_INSTANCE, "pg8000", **connect_kwargs_fallback)
                return conn
            except Exception as e2:
                logger.error("IAM fallback using ADC token failed: %s", e2)
                raise

        # If not IAM or all attempts failed, re-raise the original exception
        raise

    driver_name = "psycopg2" if CLOUD_SQL_IAM_AUTH else "pg8000"
    engine = create_engine(
        f"postgresql+{driver_name}://",
        creator=getconn,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
    )

    logger.info("Using Cloud SQL Python Connector for instance %s", CLOUD_SQL_INSTANCE)
    return engine


# Create engine: prefer Cloud SQL connector when CLOUD_SQL_INSTANCE is provided
if CLOUD_SQL_INSTANCE:
    try:
        engine = _create_engine_with_connector()
    except Exception as e:
        logger.error("Failed to initialize Cloud SQL connector: %s", e)
        logger.info("Falling back to DATABASE_URL: %s", DATABASE_URL)
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),   # Recycle connections every hour
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
        )
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),   # Recycle connections every hour
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