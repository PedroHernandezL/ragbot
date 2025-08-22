import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.connection import init_db, close_db
from src.api.endpoints import router
from src.bot.telegram_bot import telegram_bot
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Telegram RAG Bot with 24h Conversation Memory...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Start Telegram bot
        asyncio.create_task(telegram_bot.run())
        logger.info("Telegram bot with conversation memory started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        try:
            # Stop Telegram bot
            await telegram_bot.stop()
            logger.info("Telegram bot stopped")
            
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI application
app = FastAPI(
    title="RAG Bot API",
    description="API para bot con capacidades RAG y memoria conversacional de 24 horas",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Telegram RAG Bot API con Historial 24h",
        "version": "0.1.0",
        "status": "running",
        "features": ["24h-conversation-memory", "contextual-responses", "rag", "telegram-bot"]
    }

@app.get("/info")
async def info():
    """Get application information"""
    return {
        "name": "Telegram RAG Bot con Historial Inteligente",
        "version": "0.1.0",
        "description": "Bot de Telegram con capacidades RAG y memoria conversacional de 24 horas",
        "features": [
            "Bot de Telegram interactivo con comandos avanzados",
            "Procesamiento de documentos PDF",
            "Búsqueda semántica con embeddings de OpenAI",
            "Base de datos vectorial con PostgreSQL + pgvector",
            "Memoria conversacional de 24 horas",
            "Respuestas contextuales basadas en historial",
            "API REST para gestión completa",
            "Estadísticas detalladas de uso"
        ],
        "new_in_v0.1.0": [
            "Historial de conversación de 24 horas",
            "Comandos /historial y /stats en Telegram",
            "Respuestas más contextuales",
            "API endpoint para historial de conversaciones",
            "Métricas avanzadas de memoria conversacional"
        ],
        "endpoints": {
            "upload_pdf": "/api/v1/upload-pdf",
            "query": "/api/v1/query (ahora con historial)",
            "conversations": "/api/v1/conversations/{user_id}",
            "documents": "/api/v1/documents",
            "stats": "/api/v1/stats (mejoradas)",
            "health": "/api/v1/health"
        },
        "telegram_commands": [
            "/start - Bienvenida con estadísticas",
            "/help - Ayuda detallada sobre memoria",
            "/historial - Ver resumen de conversaciones",
            "/stats - Estadísticas detalladas personales"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server with 24h conversation memory on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )