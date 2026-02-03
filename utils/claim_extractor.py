"""
Claim Extractor - Uses Llama to extract health claims
With automatic translation to English for better verification
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from groq import Groq


@dataclass
class HealthClaim:
    claim_text: str           # Original claim (any language)
    claim_english: str        # English translation
    category: str
    confidence: float
    original_context: str


class ClaimExtractor:
    """Extract health claims with automatic English translation."""
    
    EXTRACTION_PROMPT = """You are a health claim extraction expert. Analyze this transcript and extract ALL health-related claims.

IMPORTANT: The transcript may be in Hindi, Urdu, English, or mixed languages. 
You MUST provide BOTH the original claim AND its English translation.

For each claim provide:
1. claim_text: The exact claim in ORIGINAL language as spoken
2. claim_english: ENGLISH translation of the claim (for fact-checking)
3. category: (nutrition, medicine, fitness, mental_health, alternative_medicine, supplements, disease_prevention, weight_loss, skin_care, other)
4. confidence: 0-1 score
5. original_context: The sentence where claim appears

Transcript:
{transcript}

Respond ONLY in valid JSON:
{{
    "claims": [
        {{
            "claim_text": "original claim in any language",
            "claim_english": "English translation of the claim",
            "category": "category",
            "confidence": 0.95,
            "original_context": "context sentence"
        }}
    ],
    "total_claims": 1,
    "summary": "brief summary in English",
    "detected_language": "hindi/urdu/english/mixed"
}}"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY in .env")
        
        self.client = Groq(api_key=self.api_key)
    
    def extract_claims(self, transcript: str) -> Dict:
        if not transcript or len(transcript.strip()) < 10:
            return {"claims": [], "total_claims": 0, "summary": "Transcript too short."}
        
        prompt = self.EXTRACTION_PROMPT.format(transcript=transcript[:8000])
        
        try:
            print("[*] Extracting claims with Llama 3...")
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
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
        except:
            result = {"claims": [], "total_claims": 0, "summary": "Parse failed"}
        
        # Log detected language
        detected_lang = result.get("detected_language", "unknown")
        print(f"[*] Detected language: {detected_lang}")
        
        claims = []
        for c in result.get("claims", []):
            claim_text = c.get("claim_text", "")
            claim_english = c.get("claim_english", claim_text)  # Fallback to original
            
            # If no English translation provided, use original
            if not claim_english:
                claim_english = claim_text
            
            claims.append(HealthClaim(
                claim_text=claim_text,
                claim_english=claim_english,
                category=c.get("category", "other"),
                confidence=float(c.get("confidence", 0.5)),
                original_context=c.get("original_context", "")
            ))
            
            # Log the translation
            if claim_text != claim_english:
                print(f"    Original: {claim_text[:50]}...")
                print(f"    English:  {claim_english[:50]}...")
        
        return {
            "claims": claims,
            "total_claims": len(claims),
            "summary": result.get("summary", ""),
            "detected_language": detected_lang,
            "raw_response": result
        }
    
    def categorize_claims(self, claims: List[HealthClaim]) -> Dict[str, List[HealthClaim]]:
        categorized = {}
        for claim in claims:
            if claim.category not in categorized:
                categorized[claim.category] = []
            categorized[claim.category].append(claim)
        return categorized