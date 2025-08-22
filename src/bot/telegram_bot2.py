import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from src.models.database import User, Conversation, Document
from src.database.connection import get_db, SessionLocal
from src.services.rag_service import rag_service
from config.settings import settings

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
        """Setup command and message handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("historial", self.history_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Get or create user in database
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
            
            if not db_user:
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                
                welcome_message = f"""
¡Hola {user.first_name}! 👋

Bienvenido al **Bot RAG con Historial Inteligente** 🧠

**¿Qué puedo hacer?**
📚 Responder preguntas sobre documentos PDF procesados
🕒 Recordar nuestras conversaciones de las últimas 24 horas
💬 Dar respuestas contextuales basadas en nuestro historial

**💡 Características especiales:**
• **Memoria de 24h**: Recuerdo lo que hemos hablado recientemente
• **Contexto inteligente**: Uso documentos + historial para respuestas más precisas
• **Conversación natural**: Puedes hacer referencias a temas anteriores

**🔍 Comandos disponibles:**
/start - Reiniciar el bot

🚀 **¡Comienza haciendo una pregunta y veamos cómo puedo ayudarte!**
"""
            else:
                # Get conversation summary for returning user
                summary = await rag_service.get_conversation_summary(db_user.id, db)
                
                welcome_message = f"""
¡Hola de nuevo {user.first_name}! 👋

📊 **Tu actividad:**
• Total de conversaciones: **{summary['total_conversations']}**
• Conversaciones últimas 24h: **{summary['conversations_24h']}**

🧠 **Recuerdo nuestras conversaciones recientes**, así que puedes hacer referencias a temas que hemos discutido antes.

💬 **¿En qué puedo ayudarte hoy?**
"""
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Ha ocurrido un error. Por favor, inténtalo de nuevo.")
        finally:
            db.close()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Bot RAG con Historial Inteligente**

Este bot utiliza **Retrieval Augmented Generation (RAG)** combinado con **memoria conversacional** para responder tus preguntas.

**🧠 ¿Cómo funciona la memoria?**
• Recuerdo **todas las conversaciones** de las últimas 24 horas
• Uso ese contexto para dar **respuestas más precisas**
• Puedes hacer referencias como "*como mencionaste antes*" o "*sobre lo que hablamos*"

**📚 ¿Cómo funciona el RAG?**
• Busco información en documentos PDF procesados
• Combino esa información con nuestro historial
• Genero respuestas contextuales y precisas

**💬 Ejemplos de uso:**
✅ "*¿Qué opinas del tema que discutimos ayer?*"
✅ "*Más detalles sobre lo que mencionaste antes*"
✅ "*Basándote en lo que hablamos, ¿qué recomiendas?*"

**🎯 Consejos para mejores resultados:**
• Sé específico en tus preguntas
• Haz referencias a conversaciones anteriores cuando sea relevante
• Utiliza palabras clave de los documentos

**📋 Comandos:**
/start - Reiniciar e info de bienvenida
/help - Esta ayuda
/historial - Ver resumen de conversaciones
/stats - Estadísticas de actividad

**🕒 Memoria**: Las últimas 24 horas se mantienen para contexto
**📄 Documentos**: Se procesan via API REST

¡Pregunta lo que necesites! 🚀
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /historial command - show conversation summary"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
            
            if not db_user:
                await update.message.reply_text(
                    "Por favor, usa el comando /start primero."
                )
                return
            
            # Get conversation summary
            summary = await rag_service.get_conversation_summary(db_user.id, db)
            
            # Get recent conversation topics (last 10)
            from datetime import datetime, timedelta
            recent_conversations = db.query(Conversation).filter(
                Conversation.user_id == db_user.id
            ).order_by(Conversation.created_at.desc()).limit(10).all()
            
            history_text = f"""
📊 **Resumen de tu Historial**

**📈 Estadísticas:**
• Total conversaciones: **{summary['total_conversations']}**
• Últimas 24 horas: **{summary['conversations_24h']}**
• Última actividad: **{summary['last_conversation'][:19] if summary['last_conversation'] else 'N/A'}**

**💬 Últimas conversaciones:**
"""
            
            if recent_conversations:
                for i, conv in enumerate(recent_conversations[:5], 1):
                    # Truncate message for display
                    msg_preview = conv.message[:60] + "..." if len(conv.message) > 60 else conv.message
                    time_str = conv.created_at.strftime("%d/%m %H:%M")
                    history_text += f"\n{i}. **{time_str}** - {msg_preview}"
            else:
                history_text += "\n*No hay conversaciones registradas aún.*"
            
            history_text += f"""

🧠 **Contexto activo**: Recuerdo las conversaciones de las últimas 24h para darte respuestas más inteligentes.

💡 Puedes referenciar estas conversaciones en tus nuevas preguntas.
"""
            
            await update.message.reply_text(history_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in history command: {e}")
            await update.message.reply_text("Error al obtener el historial.")
        finally:
            db.close()
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show detailed statistics"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
            
            if not db_user:
                await update.message.reply_text("Por favor, usa /start primero.")
                return
            
            # Get detailed stats
            from sqlalchemy import func, and_
            from datetime import datetime, timedelta
            
            # Time ranges
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Queries
            total_conversations = db.query(Conversation).filter(Conversation.user_id == db_user.id).count()
            today_conversations = db.query(Conversation).filter(
                and_(Conversation.user_id == db_user.id, Conversation.created_at >= today)
            ).count()
            week_conversations = db.query(Conversation).filter(
                and_(Conversation.user_id == db_user.id, Conversation.created_at >= week_ago)
            ).count()
            
            # Average message length
            avg_query_length = db.query(func.avg(func.length(Conversation.message))).filter(
                Conversation.user_id == db_user.id
            ).scalar() or 0
            
            stats_text = f"""
📊 **Estadísticas Detalladas**

**👤 Usuario:** {user.first_name}
**📅 Miembro desde:** {db_user.created_at.strftime('%d/%m/%Y')}

**💬 Conversaciones:**
• Hoy: **{today_conversations}**
• Esta semana: **{week_conversations}**
• Total: **{total_conversations}**

**📝 Análisis de mensajes:**
• Longitud promedio: **{avg_query_length:.0f}** caracteres

**🧠 Sistema de memoria:**
• Contexto activo: **Últimas 24 horas**
• Conversaciones en memoria: **{db.query(Conversation).filter(and_(Conversation.user_id == db_user.id, Conversation.created_at >= (now - timedelta(hours=24)))).count()}**

**📚 Base de conocimiento:**
• Documentos procesados: **{db.query(func.count(func.distinct(Document.filename))).scalar() or 0}**
• Chunks de información: **{db.query(Document).count()}**

💡 **Tip**: Mientras más conversemos, mejor entenderé tu contexto y preferencias.
"""
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("Error al obtener estadísticas.")
        finally:
            db.close()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with 24h conversation context"""
        user = update.effective_user
        message_text = update.message.text
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        db = SessionLocal()
        try:
            # Get user from database
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
            
            if not db_user:
                await update.message.reply_text(
                    "Por favor, usa el comando /start para comenzar."
                )
                return
            
            # Get RAG response with 24h conversation history
            response = await rag_service.get_response(
                query=message_text,
                user_id=db_user.id,
                db=db
            )
            
            # Save current conversation
            conversation = Conversation(
                user_id=db_user.id,
                message=message_text,
                response=response
            )
            db.add(conversation)
            db.commit()
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "Lo siento, ha ocurrido un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
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