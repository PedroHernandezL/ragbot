import PyPDF2
import pdfplumber
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from src.models.database import Document, Conversation
from src.services.openai_service import openai_service
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        logger.info(f"Extracting text from PDF: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} pages")
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        logger.info(f"Extracted text from page {page_num + 1}")
        except Exception as e:
            logger.error(f"Error extracting text with pdfplumber: {e}")
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    logger.info(f"Fallback to PyPDF2, PDF has {len(reader.pages)} pages")
                    for page_num, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                            logger.info(f"Extracted text from page {page_num + 1} with PyPDF2")
            except Exception as e2:
                logger.error(f"Error extracting text with PyPDF2: {e2}")
                raise
        
        logger.info(f"Total text extracted: {len(text)} characters")
        return text

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end < len(text):
                for break_char in ['\n\n', '. ', '.\n', '!\n', '?\n']:
                    break_pos = text.rfind(break_char, start, end)
                    if break_pos > start:
                        end = break_pos + len(break_char)
                        break
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
        
        logger.info(f"Text split into {len(chunks)} chunks")
        return chunks

    async def process_pdf(self, pdf_path: str, db: Session) -> bool:
        """Process PDF file and store embeddings in database"""
        try:
            logger.info(f"Starting PDF processing: {pdf_path}")
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.error("No text extracted from PDF")
                return False

            # Chunk text
            chunks = self.chunk_text(text)
            filename = os.path.basename(pdf_path)
            
            logger.info(f"Processing {len(chunks)} chunks for {filename}")

            # Process all chunks in batches instead of individual commits
            successful_chunks = 0
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)}")
                    embedding = await openai_service.generate_embedding(chunk)
                    
                    logger.info(f"Embedding generated successfully, length: {len(embedding)}")
                    
                    document = Document(
                        filename=filename,
                        content=chunk,
                        embedding=embedding,
                        chunk_index=i
                    )
                    
                    db.add(document)
                    
                    # Commit every 5 chunks to avoid large transactions
                    if (i + 1) % 5 == 0:
                        db.commit()
                        logger.info(f"Committed chunks {i-3} to {i+1}")
                    
                    successful_chunks += 1
                    logger.info(f"Processed chunk {i+1}/{len(chunks)} for {filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {i}: {e}")
                    db.rollback()
                    continue

            # Final commit for remaining chunks
            try:
                db.commit()
                logger.info(f"Final commit completed")
            except Exception as e:
                logger.error(f"Error in final commit: {e}")
                db.rollback()
                return False

            logger.info(f"Successfully processed PDF: {filename} ({successful_chunks}/{len(chunks)} chunks)")
            return successful_chunks > 0
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            try:
                db.rollback()
            except:
                pass
            return False

    async def search_similar_content(self, query: str, db: Session, limit: int = 3) -> List[str]:
        try:
            # Generar embedding con OpenAI
            query_embedding = await openai_service.generate_embedding(query)
            
            # Convertir a lista si es ndarray
            embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
            
            # Convertir lista a representación tipo string para SQL
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            # Realizar búsqueda usando similaridad con pgvector
            sql = text(f"""
                SELECT content, embedding <-> '{embedding_str}'::vector AS distance
                FROM documents
                ORDER BY distance
                LIMIT :limit
            """)
            
            result = db.execute(sql, {"limit": limit})
            similar_content = [row[0] for row in result]
            return similar_content
        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []

    async def get_conversation_history_24h(self, user_id: int, db: Session) -> List[dict]:
        """Get conversation history from last 24 hours"""
        try:
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            conversations = db.query(Conversation).filter(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.created_at >= twenty_four_hours_ago
                )
            ).order_by(Conversation.created_at.asc()).all()

            history = []
            for conv in conversations:
                history.append({"role": "user", "content": conv.message})
                history.append({"role": "assistant", "content": conv.response})

            logger.info(f"Retrieved {len(conversations)} conversations from last 24h for user {user_id}")
            return history
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def get_response(self, query: str, user_id: int, db: Session) -> str:
        """Get RAG response for user query with 24h conversation context"""
        try:
            similar_content = await self.search_similar_content(query, db)
            conversation_history_24h = await self.get_conversation_history_24h(user_id, db)

            if similar_content:
                context = "\n\n".join(similar_content)
            else:
                context = "No se encontró información relevante en los documentos procesados."

            response = await openai_service.generate_response(
                query=query,
                context=context,
                conversation_history_24h=conversation_history_24h
            )

            """ if not similar_content and not conversation_history_24h:
                response += "\n\n💡 Nota: No encontré información relevante en los documentos ni historial previo. Asegúrate de que los documentos hayan sido procesados correctamente."
            elif not similar_content:
                response += "\n\n💡 Nota: Basé esta respuesta en nuestro historial de conversación, ya que no encontré información específica en los documentos." """

            return response
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return "Lo siento, ha ocurrido un error al procesar tu consulta."

    async def get_conversation_summary(self, user_id: int, db: Session) -> dict:
        """Get summary of user's conversation activity"""
        try:
            total_conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).count()

            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            recent_conversations = db.query(Conversation).filter(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.created_at >= twenty_four_hours_ago
                )
            ).count()

            last_conversation = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.created_at.desc()).first()

            return {
                "total_conversations": total_conversations,
                "conversations_24h": recent_conversations,
                "last_conversation": last_conversation.created_at.isoformat() if last_conversation else None
            }
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {
                "total_conversations": 0,
                "conversations_24h": 0,
                "last_conversation": None
            }

rag_service = RAGService()