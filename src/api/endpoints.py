from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from src.database.connection import get_db, SessionLocal
from src.database import connection
from src.services.rag_service import rag_service
from src.models.database import Document, User, Conversation
from src.services.pdf_section_processor_service import PDFSectionProcessor
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["RAG API"])

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[int] = None
    include_history: bool = True

class QueryResponse(BaseModel):
    response: str
    sources_count: int
    used_history: bool
    history_messages_count: int

class DocumentInfo(BaseModel):
    id: int
    filename: str
    chunks_count: int
    created_at: str

class ConversationHistory(BaseModel):
    id: int
    message: str
    response: str
    created_at: str

@router.post("/upload-pdf", summary="Upload and process PDF document")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        background_tasks.add_task(process_pdf_background, temp_file_path, file.filename)
        return {
            "message": f"PDF '{file.filename}' uploaded successfully. Processing in background.",
            "filename": file.filename,
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail="Error uploading PDF file")

async def process_pdf_background(file_path: str, filename: str):
    db = SessionLocal()
    try:
        success = await rag_service.process_pdf(file_path, db)
        if success:
            logger.info(f"Successfully processed PDF: {filename}")
        else:
            logger.error(f"Failed to process PDF: {filename}")
    except Exception as e:
        logger.error(f"Error in background PDF processing: {e}")
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/query", response_model=QueryResponse, summary="Query with conversation history")
async def query_knowledge_base(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query the RAG knowledge base with optional conversation history from last 24h
    """
    try:
        # Get similar content count for metadata
        similar_content = await rag_service.search_similar_content(request.query, db)
        sources_count = len(similar_content)
        
        history_count = 0
        used_history = False
        
        if request.user_id and request.include_history:
            # Get conversation history from last 24 hours
            history = await rag_service.get_conversation_history_24h(request.user_id, db)
            history_count = len(history) // 2  # Divide by 2 since each conversation has user + assistant message
            used_history = history_count > 0
            
            # Get RAG response with history
            response = await rag_service.get_response(
                query=request.query,
                user_id=request.user_id,
                db=db
            )
        else:
            # Get RAG response without user-specific history
            if similar_content:
                context = "\n\n".join(similar_content)
            else:
                context = "No se encontró información relevante en los documentos procesados."
            
            from src.services.openai_service import openai_service
            response = await openai_service.generate_response(
                query=request.query,
                context=context,
                conversation_history_24h=None
            )
        
        return QueryResponse(
            response=response,
            sources_count=sources_count,
            used_history=used_history,
            history_messages_count=history_count
        )
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Error processing query")

@router.get("/conversations/{user_id}", response_model=List[ConversationHistory], summary="Get user conversation history")
async def get_user_conversations(
    user_id: int,
    hours: int = 24,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get conversation history for a specific user
    """
    try:
        from sqlalchemy import and_
        
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        conversations = db.query(Conversation).filter(
            and_(
                Conversation.user_id == user_id,
                Conversation.created_at >= time_threshold
            )
        ).order_by(Conversation.created_at.desc()).limit(limit).all()
        
        return [
            ConversationHistory(
                id=conv.id,
                message=conv.message,
                response=conv.response,
                created_at=conv.created_at.isoformat()
            ) for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Error getting user conversations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversations")

@router.get("/documents", response_model=List[DocumentInfo], summary="List processed documents")
async def list_documents(db: Session = Depends(get_db)):
    """
    List all processed documents in the knowledge base
    """
    try:
        # Get unique documents with chunk counts
        from sqlalchemy import func
        
        documents = db.query(
            Document.filename,
            func.count(Document.id).label('chunks_count'),
            func.min(Document.created_at).label('created_at'),
            func.min(Document.id).label('id')
        ).group_by(Document.filename).all()
        
        document_list = []
        for doc in documents:
            document_list.append(DocumentInfo(
                id=doc.id,
                filename=doc.filename,
                chunks_count=doc.chunks_count,
                created_at=doc.created_at.isoformat()
            ))
        
        return document_list
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving documents")

@router.delete("/documents/{filename}", summary="Delete document from knowledge base")
async def delete_document(filename: str, db: Session = Depends(get_db)):
    """
    Delete a document and all its chunks from the knowledge base
    """
    try:
        # Delete all chunks for the document
        deleted_count = db.query(Document).filter(Document.filename == filename).delete()
        db.commit()
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "message": f"Document '{filename}' deleted successfully",
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting document")

@router.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "telegram-rag-bot", "features": ["24h-conversation-memory"]}

@router.get("/stats", summary="Get knowledge base statistics")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the knowledge base including conversation history
    """
    try:
        from sqlalchemy import func
        
        # Count total documents and chunks
        total_chunks = db.query(func.count(Document.id)).scalar()
        unique_documents = db.query(func.count(func.distinct(Document.filename))).scalar()
        total_users = db.query(func.count(User.id)).scalar()
        total_conversations = db.query(func.count(Conversation.id)).scalar()
        
        # Get 24h stats
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        conversations_24h = db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= twenty_four_hours_ago
        ).scalar()
        
        active_users_24h = db.query(func.count(func.distinct(Conversation.user_id))).filter(
            Conversation.created_at >= twenty_four_hours_ago
        ).scalar()
        
        return {
            "knowledge_base": {
                "total_documents": unique_documents,
                "total_chunks": total_chunks
            },
            "users": {
                "total_users": total_users,
                "active_users_24h": active_users_24h
            },
            "conversations": {
                "total_conversations": total_conversations,
                "conversations_24h": conversations_24h
            },
            "memory": {
                "conversation_memory_hours": 24,
                "active_conversations_in_memory": conversations_24h
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")
    
@router.get("/diagnose", summary="Diagnose system status")
async def diagnose_system(db: Session = Depends(get_db)):
    """Diagnose system components"""
    try:
        # Test database connection
        result = db.execute(text("SELECT 1"))
        db_status = "OK"
        
        # Test pgvector extension
        try:
            result = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            pgvector_installed = result.fetchone() is not None
        except:
            pgvector_installed = False
            
        # Test vector operations
        vector_ops_working = False
        if pgvector_installed:
            try:
                db.execute(text("SELECT '[1,2,3]'::vector"))
                vector_ops_working = True
            except:
                pass
        
        # Count documents
        doc_count = db.query(func.count(Document.id)).scalar()
        
        return {
            "database_connection": db_status,
            "pgvector_installed": pgvector_installed,
            "vector_operations_working": vector_ops_working,
            "documents_count": doc_count,
            "status": "OK" if all([db_status == "OK", pgvector_installed, vector_ops_working]) else "ISSUES_FOUND"
        }
        
    except Exception as e:
        logger.error(f"Error in system diagnosis: {e}")
        return {"error": str(e), "status": "ERROR"}
    
@router.post("/upload-pdf-sections", summary="Upload PDF and process in sections (chapters)")
async def upload_pdf_sections(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Pass only the file path to the background task; open db session inside task
        background_tasks.add_task(process_pdf_sections_background, tmp_path, file.filename)

        return {
            "message": f"PDF {file.filename} uploaded. Processing by sections started in background."
        }
    except Exception as e:
        logger.error(f"Error uploading PDF (sections): {e}")
        raise HTTPException(status_code=500, detail="Error uploading PDF")

async def process_pdf_sections_background(file_path: str, filename: str):
    db = connection.SessionLocal()
    try:
        processor = PDFSectionProcessor(db)
        await processor.process_pdf_in_sections(file_path)
        logger.info(f"PDF {filename} processed in sections successfully.")
    except Exception as e:
        logger.error(f"Error processing PDF {filename} in sections: {e}")
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)