"""
Pydantic schemas for API request/response validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class FactCheckRequest(BaseModel):
    """Request schema for fact-checking a video."""
    url: str = Field(..., description="Instagram Reel URL")
    language: str = Field(default="english", description="Language for transcription")


class ClaimVerdictSchema(BaseModel):
    """Schema for a single claim verdict."""
    claim: str
    verdict: str
    confidence: float
    explanation: str
    evidence: List[Dict[str, Any]]
    sources: List[str]
    category: str


class FactCheckResponse(BaseModel):
    """Response schema for fact-check results."""
    id: Optional[int] = None
    url: str
    transcript: str
    claims_found: int
    verdicts: List[ClaimVerdictSchema]
    overall_rating: str
    overall_confidence: float
    summary: str
    timestamp: str
    language: str


class ChatRequest(BaseModel):
    """Request schema for chat."""
    fact_check_id: int
    question: str


class ChatResponse(BaseModel):
    """Response schema for chat."""
    answer: str
    fact_check_id: int


class HistoryItem(BaseModel):
    """Schema for history list items."""
    id: int
    url: str
    shortcode: Optional[str]
    overall_rating: str
    claims_found: int
    summary: str
    created_at: str