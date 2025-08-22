import os
import re
from typing import List
import pdfplumber
from src.services.openai_service import openai_service
from src.models.database import Document
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class PDFSectionProcessor:
    def __init__(self, session: Session, chunk_size: int = 3000, chunk_overlap: int = 200):
        self.db = session
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_sections(self, pdf_path: str) -> List[str]:
        """Extrae texto dividido en secciones basadas en títulos y páginas"""
        sections = []
        current_section = ""
        title_pattern = re.compile(r'^(Capítulo|Capitulo|Chapter|Sección|Section|Parte|Parte)\b', re.I)

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    continue
                lines = text.splitlines()
                # Buscar título en líneas
                for line in lines:
                    if title_pattern.match(line.strip()):
                        # Nuevo capítulo detectado, guardar sección anterior
                        if current_section.strip():
                            sections.append(current_section.strip())
                            current_section = ""
                        current_section += line + "\n"
                    else:
                        current_section += line + "\n"
                # Si es última página, agregar la sección
                if page_num == len(pdf.pages) and current_section.strip():
                    sections.append(current_section.strip())
        logger.info(f"PDF dividido en {len(sections)} secciones")
        return sections

    def chunk_text(self, text: str) -> List[str]:
        """Dividir texto en chunks con overlap, para embeddings"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end < len(text):
                # Buscar espacio para cortar chunks bien
                cut_pos = text.rfind(" ", start, end)
                if cut_pos != -1 and cut_pos > start:
                    end = cut_pos
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
        logger.info(f"Sección dividida en {len(chunks)} chunks")
        return chunks

    async def process_section(self, section_text: str, section_index: int, pdf_name: str):
        """Genera embeddings por chunks de la sección y guarda en base"""
        chunks = self.chunk_text(section_text)
        saved_chunks = 0
        for i, chunk in enumerate(chunks):
            try:
                embedding = await openai_service.generate_embedding(chunk)
                doc_chunk = Document(
                    filename=f"{pdf_name}_section{section_index}",
                    content=chunk,
                    embedding=embedding,
                    chunk_index=i
                )
                self.db.add(doc_chunk)
                if (i + 1) % 5 == 0:
                    self.db.commit()
                saved_chunks += 1
            except Exception as e:
                logger.error(f"Error creando embedding chunk {i} sección {section_index}: {e}")
                self.db.rollback()
                continue
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error en commit final sección {section_index}: {e}")
            self.db.rollback()
        logger.info(f"Sección {section_index} procesada con {saved_chunks} chunks guardados")

    async def process_pdf_in_sections(self, pdf_path: str):
        """Procesa el pdf dividiéndolo en secciones y generando embeddings por sección"""
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        sections = self.extract_sections(pdf_path)
        for idx, section in enumerate(sections):
            await self.process_section(section, idx + 1, pdf_name)