import logging
import json
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    DiscoveryQuestionSet, DiscoveryQuestionSetStatus, DiscoveryQuestion,
    Document, DiscoveryQuestionScope, SummaryPack, SummaryPackStatus,
    DiscoveryQuestionCategory, DiscoveryQuestionPriority, DiscoveryQuestionStatus
)
from app.services.rag_service import answer_question
from app.config import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

def generate_discovery_questions_task(question_set_id: UUID):
    """Background task to generate discovery questions."""
    print(f"DEBUG: Starting generate_discovery_questions_task for {question_set_id}", flush=True)
    db = SessionLocal()
    try:
        q_set = db.query(DiscoveryQuestionSet).filter(DiscoveryQuestionSet.id == question_set_id).first()
        if not q_set:
            logger.error(f"DiscoveryQuestionSet {question_set_id} not found")
            return

        q_set.status = DiscoveryQuestionSetStatus.IN_PROGRESS
        db.commit()

        # 1. Gather Context
        context_text = ""
        
        # Option A: Reuse most recent successful SummaryPack
        latest_summary = db.query(SummaryPack).filter(
            SummaryPack.notebook_id == q_set.notebook_id,
            SummaryPack.status == SummaryPackStatus.DONE
        ).order_by(SummaryPack.created_at.desc()).first()

        if latest_summary and latest_summary.sections:
            print("DEBUG: Using existing SummaryPack for context", flush=True)
            # Extract relevant parts from summary pack
            sections = latest_summary.sections
            if isinstance(sections, dict):
                exec_summary = sections.get("executive_summary", "")
                context_text += f"Executive Summary:\n{exec_summary}\n\n"
                
                # Add individual document summaries if available
                for key, value in sections.items():
                    if key != "executive_summary" and isinstance(value, dict):
                        doc_name = value.get("document_name", "Document")
                        doc_summary = value.get("summary", "")
                        context_text += f"Document: {doc_name}\nSummary: {doc_summary}\n\n"

        # Option B: If no summary pack, or if we want more detail, we could sample documents.
        # For now, let's rely on SummaryPack if available, otherwise fetch summaries for documents.
        
        if not context_text:
            print("DEBUG: No SummaryPack found, generating fresh context from documents", flush=True)
            # Identify documents
            docs_to_process = []
            if q_set.scope_type == DiscoveryQuestionScope.NOTEBOOK:
                docs_to_process = db.query(Document).filter(Document.notebook_id == q_set.notebook_id).all()
            elif q_set.scope_type == DiscoveryQuestionScope.DOCUMENT_LIST:
                if q_set.scope_document_ids:
                    doc_ids = [UUID(str(id)) for id in q_set.scope_document_ids]
                    docs_to_process = db.query(Document).filter(Document.id.in_(doc_ids)).all()
            
            if not docs_to_process:
                q_set.status = DiscoveryQuestionSetStatus.FAILED
                q_set.error_message = "No documents found to analyze."
                db.commit()
                return

            # Generate quick summaries for context
            # Limit to 5 docs to avoid context limit if too many
            for doc in docs_to_process[:5]: 
                try:
                    summary, _ = answer_question(
                        user_id=q_set.created_by_user_id,
                        notebook_id=q_set.notebook_id,
                        question="Summarize this document for discovery analysis.",
                        history=[],
                        selected_document_ids=[doc.id],
                        mode="plan"
                    )
                    context_text += f"Document: {doc.title}\nSummary: {summary}\n\n"
                except Exception as e:
                    logger.error(f"Failed to summarize doc {doc.id}: {e}")

        if not context_text:
             q_set.status = DiscoveryQuestionSetStatus.FAILED
             q_set.error_message = "Failed to gather context from documents."
             db.commit()
             return

        # 2. Generate Questions with Gemini
        print("DEBUG: Calling Gemini to generate questions...", flush=True)
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.4
        )

        prompt = f"""
        You are a senior consultant. Based on the following project context, create a list of discovery questions to clarify gaps, assumptions, and risks.
        
        Target Audience: {q_set.target_audience}
        
        Context:
        {context_text}
        
        Output a JSON array of objects with the following keys:
        - text: The question text.
        - category: One of [requirements, data, architecture, risks, operations, other].
        - priority: One of [low, medium, high].
        - related_document_name: (Optional) Name of the document this question relates to.
        
        Example JSON:
        [
            {{
                "text": "What is the expected daily data volume?",
                "category": "data",
                "priority": "high"
            }}
        ]
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Handle potential list content (multipart response)
        if isinstance(content, list):
            new_content = []
            for item in content:
                if isinstance(item, str):
                    new_content.append(item)
                elif isinstance(item, dict) and "text" in item:
                    new_content.append(item["text"])
                elif hasattr(item, "text"):
                     new_content.append(item.text)
                else:
                    new_content.append(str(item))
            content = "".join(new_content)

        print(f"DEBUG: Raw Gemini content: {content!r}", flush=True)
        
        # Parse JSON
        questions_data = []
        try:
            # Clean up potential markdown code blocks
            clean_content = content.strip()
            if "```json" in clean_content:
                clean_content = clean_content.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_content:
                clean_content = clean_content.split("```")[1].split("```")[0].strip()
            
            # Fallback: Try to find the first [ and last ]
            if not clean_content.startswith("["):
                start_idx = clean_content.find("[")
                end_idx = clean_content.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    clean_content = clean_content[start_idx:end_idx+1]
            
            print(f"DEBUG: Cleaned content for JSON parsing: {clean_content!r}", flush=True)
            questions_data = json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini: {e}")
            print(f"DEBUG: JSON Parse Error: {e}", flush=True)
            q_set.status = DiscoveryQuestionSetStatus.FAILED
            q_set.error_message = f"Failed to parse generated questions: {e}"
            db.commit()
            return

        # 3. Save Questions
        print(f"DEBUG: Saving {len(questions_data)} questions...", flush=True)
        for q_data in questions_data:
            # Map category and priority to enums (simple validation)
            category = q_data.get("category", "other").lower()
            if category not in ["requirements", "data", "architecture", "risks", "operations", "other"]:
                category = "other"
            
            priority = q_data.get("priority", "medium").lower()
            if priority not in ["low", "medium", "high"]:
                priority = "medium"

            # Try to find related document by name
            related_doc_id = None
            related_doc_name = q_data.get("related_document_name")
            if related_doc_name:
                # Simple case-insensitive match on title in the same notebook
                doc = db.query(Document).filter(
                    Document.notebook_id == q_set.notebook_id,
                    Document.title.ilike(f"%{related_doc_name}%")
                ).first()
                if doc:
                    related_doc_id = doc.id

            new_q = DiscoveryQuestion(
                question_set_id=q_set.id,
                text=q_data.get("text", "Unknown Question"),
                category=DiscoveryQuestionCategory(category),
                priority=DiscoveryQuestionPriority(priority),
                status=DiscoveryQuestionStatus.OPEN,
                related_document_id=related_doc_id
            )
            db.add(new_q)
        
        q_set.status = DiscoveryQuestionSetStatus.DONE
        db.commit()
        print("DEBUG: Discovery generation completed successfully", flush=True)

    except Exception as e:
        logger.error(f"Discovery generation failed: {e}")
        print(f"DEBUG: Discovery generation failed: {e}", flush=True)
        try:
            q_set.status = DiscoveryQuestionSetStatus.FAILED
            q_set.error_message = str(e)
            db.commit()
        except:
            pass
    finally:
        db.close()
