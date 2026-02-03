"""
Claim Extractor - Uses Llama to extract health claims
Simplified Groq initialization
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class HealthClaim:
    claim_text: str
    claim_english: str
    category: str
    confidence: float
    original_context: str


class ClaimExtractor:
    """Extract health claims with automatic English translation."""
    
    CATEGORIES = [
        "nutrition", "medicine", "fitness", "mental_health",
        "alternative_medicine", "supplements", "disease_prevention",
        "weight_loss", "skin_care", "sleep", "detox_cleanse",
        "immunity", "chronic_disease", "pregnancy_child_health",
        "aging", "other"
    ]
    
    EXTRACTION_PROMPT = """You are a health claim extraction expert. Analyze this transcript and extract ALL health-related claims.

IMPORTANT: The transcript may be in Hindi, Urdu, English, or mixed languages. 
You MUST provide BOTH the original claim AND its English translation.

For each claim provide:
1. claim_text: The exact claim in ORIGINAL language as spoken
2. claim_english: ENGLISH translation of the claim
3. category: One of {categories}
4. confidence: 0-1 score
5. original_context: The sentence where claim appears

Transcript:
{transcript}

Respond ONLY in valid JSON:
{{
    "claims": [
        {{
            "claim_text": "original claim",
            "claim_english": "English translation",
            "category": "category",
            "confidence": 0.95,
            "original_context": "context"
        }}
    ],
    "total_claims": 1,
    "summary": "brief summary",
    "detected_language": "hindi/urdu/english/mixed"
}}"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required.")
        
        self.client = self._initialize_groq_client()
    
    def _initialize_groq_client(self):
        """Initialize Groq client"""
        try:
            from groq import Groq
            return Groq(api_key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Groq: {e}")
    
    def extract_claims(self, transcript: str) -> Dict:
        """Extract health claims from transcript"""
        if not transcript or len(transcript.strip()) < 10:
            return {
                "claims": [], 
                "total_claims": 0, 
                "summary": "Transcript too short.",
                "detected_language": "unknown"
            }
        
        categories_str = ", ".join(self.CATEGORIES)
        prompt = self.EXTRACTION_PROMPT.format(
            transcript=transcript[:8000],
            categories=categories_str
        )
        
        try:
            print("[*] Extracting claims with Llama 3.3...")
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            response_text = response.choices[0].message.content
            print("[*] Extraction successful!")
            
        except Exception as e:
            print(f"[ERROR] Groq API Error: {e}")
            raise ValueError(f"Groq API Error: {e}")
        
        # Parse JSON
        try:
            clean_text = response_text.strip()
            
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0]
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0]
            
            start = clean_text.find("{")
            end = clean_text.rfind("}") + 1
            if start != -1 and end > start:
                clean_text = clean_text[start:end]
            
            result = json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parse error: {e}")
            result = {
                "claims": [], 
                "total_claims": 0, 
                "summary": "Parse failed",
                "detected_language": "unknown"
            }
        
        detected_lang = result.get("detected_language", "unknown")
        print(f"[*] Detected language: {detected_lang}")
        print(f"[*] Found {len(result.get('claims', []))} claims")
        
        claims = []
        for c in result.get("claims", []):
            claim_text = c.get("claim_text", "")
            claim_english = c.get("claim_english", claim_text)
            
            if not claim_english:
                claim_english = claim_text
            
            category = c.get("category", "other")
            if category not in self.CATEGORIES:
                category = "other"
            
            claims.append(HealthClaim(
                claim_text=claim_text,
                claim_english=claim_english,
                category=category,
                confidence=float(c.get("confidence", 0.5)),
                original_context=c.get("original_context", "")
            ))
            
            if claim_text != claim_english:
                print(f"    📝 Original: {claim_text[:60]}...")
                print(f"    🔤 English:  {claim_english[:60]}...")
        
        return {
            "claims": claims,
            "total_claims": len(claims),
            "summary": result.get("summary", ""),
            "detected_language": detected_lang,
            "raw_response": result
        }
    
    def categorize_claims(self, claims: List[HealthClaim]) -> Dict[str, List[HealthClaim]]:
        """Group claims by category"""
        categorized = {}
        for claim in claims:
            if claim.category not in categorized:
                categorized[claim.category] = []
            categorized[claim.category].append(claim)
        return categorized
    
    def get_high_confidence_claims(self, claims: List[HealthClaim], threshold: float = 0.7) -> List[HealthClaim]:
        """Filter claims by confidence threshold"""
        return [c for c in claims if c.confidence >= threshold]