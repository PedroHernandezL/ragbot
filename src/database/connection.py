from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import settings
from src.models.database import Base
import asyncpg
import logging
import ssl

logger = logging.getLogger(__name__)

# Synchronous database setup
engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous database setup
ssl_context = ssl.create_default_context()
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    connect_args={"ssl": ssl_context},
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

def get_db():
    """Dependency for synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Dependency for asynchronous database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables and pgvector extension"""
    try:
        # Connect directly to enable pgvector extension
        conn = await asyncpg.connect(settings.database_url)
        
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.close()
        
        logger.info("pgvector extension enabled")
        
        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def close_db():
    """Close database connections"""
    await async_engine.dispose()