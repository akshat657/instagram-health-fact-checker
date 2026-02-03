"""
Database Handler - SQLAlchemy models and operations
Supports both SQLite (local) and PostgreSQL (production)
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


class FactCheckRecord(Base):
    """Database model for fact-check records."""
    __tablename__ = "fact_checks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    shortcode = Column(String(100), index=True)
    transcript = Column(Text)
    language = Column(String(50))
    claims_found = Column(Integer, default=0)
    verdicts = Column(JSON)  # Store as JSON array
    overall_rating = Column(String(50))
    overall_confidence = Column(Float)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to chat messages
    chat_messages = relationship("ChatMessage", back_populates="fact_check", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Database model for chat history."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fact_check_id = Column(Integer, ForeignKey("fact_checks.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user or assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    fact_check = relationship("FactCheckRecord", back_populates="chat_messages")


class Database:
    """
    Database handler for storing fact-check results and chat history.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            database_url: SQLAlchemy database URL
                         Defaults to DATABASE_URL env var or SQLite
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./fact_checker.db")
        
        # Handle Heroku/Fly.io PostgreSQL URL format
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def save_fact_check(self, result: Dict[str, Any]) -> int:
        """
        Save a fact-check result to the database.
        
        Args:
            result: Fact-check result dictionary
            
        Returns:
            ID of the saved record
        """
        session = self.SessionLocal()
        try:
            # Extract shortcode from URL
            url = result.get("url", "")
            shortcode = ""
            if "/reel/" in url or "/reels/" in url or "/p/" in url:
                import re
                match = re.search(r'/(?:reels?|p)/([A-Za-z0-9_-]+)', url)
                if match:
                    shortcode = match.group(1)
            
            record = FactCheckRecord(
                url=url,
                shortcode=shortcode,
                transcript=result.get("transcript", ""),
                language=result.get("language", "english"),
                claims_found=result.get("claims_found", 0),
                verdicts=result.get("verdicts", []),
                overall_rating=result.get("overall_rating", ""),
                overall_confidence=result.get("overall_confidence", 0.0),
                summary=result.get("summary", "")
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.id
            
        finally:
            session.close()
    
    def get_fact_check(self, record_id: int) -> Optional[Dict]:
        """
        Retrieve a fact-check record by ID.
        
        Args:
            record_id: Database record ID
            
        Returns:
            Fact-check result dictionary or None
        """
        session = self.SessionLocal()
        try:
            record = session.query(FactCheckRecord).filter_by(id=record_id).first()
            if not record:
                return None
            
            return {
                "id": record.id,
                "url": record.url,
                "shortcode": record.shortcode,
                "transcript": record.transcript,
                "language": record.language,
                "claims_found": record.claims_found,
                "verdicts": record.verdicts,
                "overall_rating": record.overall_rating,
                "overall_confidence": record.overall_confidence,
                "summary": record.summary,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            
        finally:
            session.close()
    
    def get_fact_check_by_url(self, url: str) -> Optional[Dict]:
        """
        Find a fact-check by URL.
        
        Args:
            url: Instagram reel URL
            
        Returns:
            Most recent fact-check for this URL or None
        """
        session = self.SessionLocal()
        try:
            record = session.query(FactCheckRecord)\
                .filter_by(url=url)\
                .order_by(FactCheckRecord.created_at.desc())\
                .first()
            
            if not record:
                return None
            
            return {
                "id": record.id,
                "url": record.url,
                "shortcode": record.shortcode,
                "transcript": record.transcript,
                "language": record.language,
                "claims_found": record.claims_found,
                "verdicts": record.verdicts,
                "overall_rating": record.overall_rating,
                "overall_confidence": record.overall_confidence,
                "summary": record.summary,
                "created_at": record.created_at.isoformat() if record.created_at else None
            }
            
        finally:
            session.close()
    
    def get_recent_fact_checks(self, limit: int = 10) -> List[Dict]:
        """
        Get recent fact-check records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of fact-check dictionaries
        """
        session = self.SessionLocal()
        try:
            records = session.query(FactCheckRecord)\
                .order_by(FactCheckRecord.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [
                {
                    "id": r.id,
                    "url": r.url,
                    "shortcode": r.shortcode,
                    "overall_rating": r.overall_rating,
                    "claims_found": r.claims_found,
                    "summary": r.summary,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in records
            ]
            
        finally:
            session.close()
    
    def add_chat_message(self, fact_check_id: int, role: str, content: str) -> int:
        """
        Add a chat message for a fact-check.
        
        Args:
            fact_check_id: ID of the fact-check record
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            ID of the saved message
        """
        session = self.SessionLocal()
        try:
            message = ChatMessage(
                fact_check_id=fact_check_id,
                role=role,
                content=content
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message.id
            
        finally:
            session.close()
    
    def get_chat_history(self, fact_check_id: int) -> List[Dict]:
        """
        Get chat history for a fact-check.
        
        Args:
            fact_check_id: ID of the fact-check record
            
        Returns:
            List of chat messages
        """
        session = self.SessionLocal()
        try:
            messages = session.query(ChatMessage)\
                .filter_by(fact_check_id=fact_check_id)\
                .order_by(ChatMessage.created_at.asc())\
                .all()
            
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ]
            
        finally:
            session.close()
    
    def delete_fact_check(self, record_id: int) -> bool:
        """
        Delete a fact-check and its chat history.
        
        Args:
            record_id: ID of the fact-check to delete
            
        Returns:
            True if deleted, False if not found
        """
        session = self.SessionLocal()
        try:
            record = session.query(FactCheckRecord).filter_by(id=record_id).first()
            if not record:
                return False
            
            session.delete(record)
            session.commit()
            return True
            
        finally:
            session.close()