import logging
from uuid import UUID
from typing import List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SummaryPack, SummaryPackStatus, Document, SummaryPackScope
from app.services.rag_service import answer_question
from app.config import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

def generate_summary_pack_task(summary_pack_id: UUID):
    """Background task to generate summary pack."""
    print(f"DEBUG: Starting generate_summary_pack_task for {summary_pack_id}", flush=True)
    db = SessionLocal()
    try:
        print("DEBUG: Database session created", flush=True)
        pack = db.query(SummaryPack).filter(SummaryPack.id == summary_pack_id).first()
        if not pack:
            print(f"DEBUG: SummaryPack {summary_pack_id} not found", flush=True)
            logger.error(f"SummaryPack {summary_pack_id} not found")
            return

        print(f"DEBUG: Found pack {pack.id}, updating status to IN_PROGRESS", flush=True)
        pack.status = SummaryPackStatus.IN_PROGRESS
        db.commit()
        print("DEBUG: Status updated to IN_PROGRESS", flush=True)

        # 1. Identify documents
        docs_to_process = []
        if pack.scope_type == SummaryPackScope.NOTEBOOK:
            docs_to_process = db.query(Document).filter(Document.notebook_id == pack.notebook_id).all()
        elif pack.scope_type == SummaryPackScope.DOCUMENT_LIST:
            if pack.scope_document_ids:
                doc_ids = [UUID(str(id)) for id in pack.scope_document_ids]
                docs_to_process = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        
        print(f"DEBUG: Found {len(docs_to_process)} documents to process", flush=True)

        if not docs_to_process:
            pack.status = SummaryPackStatus.FAILED
            pack.error_message = "No documents found to summarize."
            db.commit()
            return

        # 2. Generate summaries for each document
        sections = {}
        combined_summaries = []

        for i, doc in enumerate(docs_to_process):
            try:
                print(f"DEBUG: Processing document {i+1}/{len(docs_to_process)}: {doc.title}", flush=True)
                logger.info(f"Summarizing document {doc.id}: {doc.title}")
                # Use RAG service to summarize specific document
                summary, _ = answer_question(
                    user_id=pack.created_by_user_id,
                    notebook_id=pack.notebook_id,
                    question="Provide a detailed summary of this document. Include key takeaways, main points, and any important dates or figures.",
                    history=[],
                    selected_document_ids=[doc.id],
                    mode="plan" # Use plan mode for detailed output
                )
                print(f"DEBUG: Summary generated for {doc.title}", flush=True)
                
                sections[str(doc.id)] = {
                    "document_name": doc.title,
                    "summary": summary
                }
                combined_summaries.append(f"Document: {doc.title}\nSummary:\n{summary}")
                
            except Exception as e:
                logger.error(f"Failed to summarize doc {doc.id}: {e}")
                sections[str(doc.id)] = {
                    "document_name": doc.title,
                    "summary": f"Error generating summary: {str(e)}"
                }

        # 3. Generate Executive Summary (Master Summary)
        if combined_summaries:
            try:
                print("DEBUG: Starting Executive Summary generation...", flush=True)
                logger.info("Generating executive summary...")
                llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=0.3
                )
                
                master_prompt = "You are a research assistant. Below are summaries of several documents. Please provide an Executive Summary that synthesizes the key information across all these documents.\n\n" + "\n\n---\n\n".join(combined_summaries)
                
                print(f"DEBUG: Sending master prompt (length: {len(master_prompt)}) to Gemini...", flush=True)
                response = llm.invoke([HumanMessage(content=master_prompt)])
                print("DEBUG: Executive Summary received from Gemini", flush=True)
                
                # Handle structured response
                content = response.content
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text_parts.append(part.get('text', ''))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    sections["executive_summary"] = "".join(text_parts)
                elif isinstance(content, dict) and content.get('type') == 'text':
                    sections["executive_summary"] = content.get('text', '')
                else:
                    sections["executive_summary"] = str(content)
                
                print("DEBUG: Executive Summary processed and saved", flush=True)

            except Exception as e:
                print(f"DEBUG: Failed to generate executive summary: {e}", flush=True)
                logger.error(f"Failed to generate executive summary: {e}")
                sections["executive_summary"] = "Failed to generate executive summary."

        # Close the long-running session to avoid timeout issues
        try:
            db.close()
            print("DEBUG: Closed long-running session", flush=True)
        except Exception as close_error:
            print(f"DEBUG: Error closing long-running session (ignoring): {close_error}", flush=True)

        # Open a fresh session for the final update
        print("DEBUG: Opening fresh DB session for final commit...", flush=True)
        final_db = SessionLocal()
        try:
            pack = final_db.query(SummaryPack).filter(SummaryPack.id == summary_pack_id).first()
            if pack:
                pack.sections = sections
                pack.status = SummaryPackStatus.DONE
                final_db.commit()
                print("DEBUG: Final commit successful", flush=True)
                logger.info(f"SummaryPack {summary_pack_id} completed successfully")
            else:
                print(f"DEBUG: SummaryPack {summary_pack_id} not found during final commit", flush=True)
                logger.error(f"SummaryPack {summary_pack_id} not found during final commit")
        except Exception as e:
            print(f"DEBUG: Error during final commit: {e}", flush=True)
            raise e
        finally:
            final_db.close()

    except Exception as e:
        logger.error(f"Summary pack generation failed: {e}")
        print(f"DEBUG: Summary pack generation failed: {e}", flush=True)
        
        # Try to update status to FAILED using a fresh session
        try:
            error_db = SessionLocal()
            pack = error_db.query(SummaryPack).filter(SummaryPack.id == summary_pack_id).first()
            if pack:
                pack.status = SummaryPackStatus.FAILED
                pack.error_message = str(e)
                error_db.commit()
            error_db.close()
        except Exception as update_error:
            logger.error(f"Failed to update status to FAILED: {update_error}")
            
    # Note: db.close() is handled above or in the finally block of the first session if we didn't close it
    # But since we closed it explicitly, we don't need a global finally for db
