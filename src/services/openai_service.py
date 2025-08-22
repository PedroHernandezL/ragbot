import openai
from typing import List, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def generate_response(
        self, 
        query: str, 
        context: str, 
        conversation_history_24h: Optional[List[dict]] = None
    ) -> str:
        """Generate response using OpenAI GPT model with 24h conversation history"""
        try:
            # Build messages for conversation
            messages = [
                {
                    "role": "system",
                    "content": f"""Eres un asistente virtual inteligente. En tu base de conocimiento, cuentas con informacion especializada de un libro de fisicacuantica llamado "Revolución Cuantica", escrito por CARLOS PEÑA BARAJAS, tu objetivo es brindar informacion,
                     responder preguntas al respecto del libro o de fisica cuantica y encaminar a los usuarios a que se interesen en los temas y que al final compren el libro.

                    Contexto de documentos:
                    {context}

                    Instrucciones:
                    - Responde en español
                    - Si la información no está en el contexto de documentos, indica que no tienes esa información
                    - Usa el historial de conversación de las últimas 24 horas para dar respuestas más contextuales
                    - Si el usuario hace referencia a algo mencionado anteriormente, úsalo para dar una respuesta más precisa
                    - Sé claro, conciso y mantén un tono amigable y profesional
                    - Si hay información contradictoria entre el historial y los documentos, prioriza los documentos pero menciona la diferencia"""
                }
            ]
            
            # Add 24-hour conversation history if provided
            if conversation_history_24h:
                # Add a separator to indicate this is recent history
                messages.append({
                    "role": "system", 
                    "content": "=== Historial de conversación de las últimas 24 horas ==="
                })
                
                # Add recent conversation history (limit to last 20 messages to avoid token limits)
                messages.extend(conversation_history_24h[-20:])
                
                messages.append({
                    "role": "system", 
                    "content": "=== Fin del historial - Responde a la nueva consulta ==="
                })
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, inténtalo de nuevo."

# Global OpenAI service instance
openai_service = OpenAIService()
