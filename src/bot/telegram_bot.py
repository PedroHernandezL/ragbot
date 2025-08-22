import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from src.models.database import User, Conversation
from src.database.connection import SessionLocal
from src.services.rag_service import rag_service
from config.settings import settings
import re


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup message handler only (conversational, no commands)"""
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message_text = update.message.text.strip()
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()

            if not db_user:
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                await update.message.reply_text(f"¡Hola {user.first_name}! Soy un asistente virtual 🤖.\nPodemos conversar sobre física cuántica cuando tú quieras.\n\n¿Te gustaría preguntarme algo específico, o prefieres charlar sobre los aspectos más curiosos del libro Revolución Cuantica? ¡Cuéntame lo que te interesa!")
                return
            
            # Obtener respuesta del rag_service
            response = await rag_service.get_response(
                query=message_text,
                user_id=db_user.id,
                db=db
            )
            
            # Crear registro de conversación
            conversation = Conversation(
                user_id=db_user.id,
                message=message_text,
                response=response
            )
            db.add(conversation)
            try:
                db.commit()
                logger.info(f"Conversación guardada: user_id={db_user.id}, message={message_text[:50]}")
            except Exception as e:
                logger.error(f"Error al guardar conversación: {e}")
                db.rollback()
            
            await update.message.reply_text(response)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error manejando mensaje: {e}")
            await update.message.reply_text(
                "Lo siento, ocurrió un error procesando tu mensaje. Por favor inténtalo de nuevo."
            )
        finally:
            db.close()
    
    async def run(self):
        """Start the bot"""
        logger.info("Starting Telegram bot with 24h conversation memory...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Telegram bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()


# Global bot instance
telegram_bot = TelegramBot()
