"""
Fact Checker - Uses English translations for better evidence matching
Supports Hindi, Urdu, English, and mixed language videos
Simplified Groq client initialization
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .evidence_finder import MultiSourceEvidenceFinder
from .claim_extractor import ClaimExtractor, HealthClaim


@dataclass
class ClaimVerdict:
    claim: str              # Original claim (displayed to user)
    claim_english: str      # English translation (used for searching)
    verdict: str
    confidence: float
    explanation: str
    evidence: List[Dict]
    sources: List[str]
    category: str


@dataclass 
class FactCheckResult:
    url: str
    transcript: str
    claims_found: int
    verdicts: List[ClaimVerdict]
    overall_rating: str
    overall_confidence: float
    summary: str
    timestamp: str
    language: str


class FactChecker:
    """Fact-checker with multi-language support."""
    
    VERIFICATION_PROMPT = """You are an expert medical fact-checker.

ORIGINAL CLAIM (in user's language): {claim_original}
ENGLISH TRANSLATION: {claim_english}

SCIENTIFIC EVIDENCE:
{evidence}

Based on the evidence, provide your verdict:
- TRUE: Claim is well-supported by evidence
- FALSE: Claim contradicts evidence
- MOSTLY_TRUE: Largely accurate with minor issues
- MOSTLY_FALSE: Has some truth but largely inaccurate
- MIXED: Partially true and partially false
- UNVERIFIED: Insufficient evidence (only if NO relevant evidence)

IMPORTANT: Base your verdict on the ENGLISH translation and evidence.
Provide explanation that references specific evidence.

Respond ONLY in valid JSON:
{{
    "verdict": "TRUE/FALSE/MOSTLY_TRUE/MOSTLY_FALSE/MIXED/UNVERIFIED",
    "confidence": 0.85,
    "explanation": "Detailed explanation in English"
}}"""

    SMART_CHAT_PROMPT = """You are a health information assistant.

VIDEO FACT-CHECK RESULTS:
{fact_check_results}

ADDITIONAL EVIDENCE:
{additional_evidence}

USER QUESTION: {question}

Provide accurate, evidence-based answer. Remind user to consult healthcare professionals."""

    def __init__(self, api_key: Optional[str] = None, ncbi_email: str = "healthchecker@example.com"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY in .env or pass as parameter.")
        
        # Initialize Groq client with ONLY the api_key parameter
        self.client = self._initialize_groq_client()
        
        self.model = "llama-3.3-70b-versatile"
        self.evidence_finder = MultiSourceEvidenceFinder(ncbi_email=ncbi_email)
        self.claim_extractor = ClaimExtractor(api_key=self.api_key)
    
    def _initialize_groq_client(self):
        """Initialize Groq client with proper error handling"""
        try:
            # Try importing groq
            from groq import Groq
            
            # Initialize with ONLY api_key - no other parameters
            client = Groq(api_key=self.api_key)
            print("[*] Groq client initialized successfully")
            return client
            
        except ImportError:
            raise ImportError(
                "Groq library not installed. Please run:\n"
                "pip install groq"
            )
        except Exception as e:
            # If initialization fails, provide helpful error message
            error_msg = str(e)
            if "proxies" in error_msg:
                raise ValueError(
                    "Groq initialization failed due to version conflict.\n"
                    "Please run these commands:\n"
                    "1. pip uninstall groq -y\n"
                    "2. pip cache purge\n"
                    "3. pip install groq==0.4.2\n"
                    "4. Restart the application"
                )
            else:
                raise ValueError(f"Failed to initialize Groq client: {error_msg}")
    
    def _verify_claim(self, claim: HealthClaim) -> ClaimVerdict:
        """Verify claim using ENGLISH translation for evidence search."""
        
        # Use English translation for searching
        search_query = claim.claim_english
        print(f"  [*] Searching (English): {search_query[:60]}...")
        
        evidence_list = self.evidence_finder.search_all_sources(search_query)
        evidence_text = self.evidence_finder.format_evidence_for_llm(evidence_list)
        
        prompt = self.VERIFICATION_PROMPT.format(
            claim_original=claim.claim_text,
            claim_english=claim.claim_english,
            evidence=evidence_text
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            response_text = response.choices[0].message.content
            
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1:
                result = json.loads(response_text[start:end])
            else:
                result = {"verdict": "UNVERIFIED", "confidence": 0.3, "explanation": "Parse error"}
                
        except Exception as e:
            print(f"  [!] Verification error: {e}")
            result = {"verdict": "UNVERIFIED", "confidence": 0.3, "explanation": str(e)}
        
        sources = [e.url for e in evidence_list if e.url]
        
        return ClaimVerdict(
            claim=claim.claim_text,
            claim_english=claim.claim_english,
            verdict=result.get("verdict", "UNVERIFIED"),
            confidence=float(result.get("confidence", 0.5)),
            explanation=result.get("explanation", ""),
            evidence=[{"source": e.source, "title": e.title, "url": e.url} for e in evidence_list],
            sources=sources,
            category=claim.category
        )
    
    def check_claims(self, transcript: str, url: str = "", language: str = "english") -> FactCheckResult:
        """Full fact-checking with multi-language support."""
        print("[*] Extracting health claims...")
        extraction_result = self.claim_extractor.extract_claims(transcript)
        claims = extraction_result["claims"]
        detected_lang = extraction_result.get("detected_language", language)
        
        print(f"[*] Detected language: {detected_lang}")
        
        if not claims:
            return FactCheckResult(
                url=url, transcript=transcript, claims_found=0, verdicts=[],
                overall_rating="NO_CLAIMS", overall_confidence=1.0,
                summary="No health claims found.",
                timestamp=datetime.now().isoformat(), language=detected_lang
            )
        
        print(f"[*] Found {len(claims)} claims. Verifying...")
        verdicts = []
        
        for i, claim in enumerate(claims):
            print(f"\n[*] Claim {i+1}/{len(claims)}:")
            print(f"    Original: {claim.claim_text[:50]}...")
            print(f"    English:  {claim.claim_english[:50]}...")
            
            verdict = self._verify_claim(claim)
            verdicts.append(verdict)
            print(f"    → {verdict.verdict} ({verdict.confidence:.0%})")
        
        overall_rating, overall_confidence = self._calculate_overall_rating(verdicts)
        summary = self._generate_summary(verdicts)
        
        return FactCheckResult(
            url=url, transcript=transcript, claims_found=len(claims),
            verdicts=verdicts, overall_rating=overall_rating,
            overall_confidence=overall_confidence, summary=summary,
            timestamp=datetime.now().isoformat(), language=detected_lang
        )
    
    def _calculate_overall_rating(self, verdicts: List[ClaimVerdict]) -> tuple:
        if not verdicts:
            return "NO_CLAIMS", 1.0
        
        counts = {}
        total_conf = 0
        
        for v in verdicts:
            counts[v.verdict] = counts.get(v.verdict, 0) + 1
            total_conf += v.confidence
        
        avg_conf = total_conf / len(verdicts)
        
        false_count = counts.get("FALSE", 0) + counts.get("MOSTLY_FALSE", 0)
        true_count = counts.get("TRUE", 0) + counts.get("MOSTLY_TRUE", 0)
        
        if false_count > len(verdicts) / 2:
            return "MOSTLY_FALSE", avg_conf
        elif false_count > 0:
            return "MIXED", avg_conf
        elif true_count > len(verdicts) / 2:
            return "MOSTLY_TRUE", avg_conf
        return "UNVERIFIED", avg_conf
    
    def _generate_summary(self, verdicts: List[ClaimVerdict]) -> str:
        counts = {}
        for v in verdicts:
            counts[v.verdict] = counts.get(v.verdict, 0) + 1
        
        emoji_map = {
            "TRUE": "✅", "MOSTLY_TRUE": "✅", 
            "FALSE": "❌", "MOSTLY_FALSE": "❌",
            "MIXED": "⚠️", "UNVERIFIED": "❓"
        }
        
        parts = [f"Analyzed {len(verdicts)} health claims."]
        for verdict, count in counts.items():
            emoji = emoji_map.get(verdict, "❓")
            parts.append(f"{emoji} {count} {verdict.lower().replace('_', ' ')}")
        
        return " ".join(parts)
    
    def chat_about_video(self, question: str, fact_check_result: FactCheckResult) -> str:
        """Smart chat with evidence search."""
        results_text = f"Overall: {fact_check_result.overall_rating}\n\n"
        for v in fact_check_result.verdicts:
            results_text += f"• {v.claim}\n  English: {v.claim_english}\n  Verdict: {v.verdict}\n\n"
        
        additional_evidence = self.evidence_finder.search_all_sources(question, max_results_per_source=2)
        additional_text = self.evidence_finder.format_evidence_for_llm(additional_evidence)
        
        prompt = self.SMART_CHAT_PROMPT.format(
            fact_check_results=results_text,
            additional_evidence=additional_text,
            question=question
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"
    
    def to_dict(self, result: FactCheckResult) -> Dict:
        """Convert FactCheckResult to dictionary"""
        return asdict(result)
    
    def dict_to_result(self, data: Dict) -> FactCheckResult:
        """Convert dictionary to FactCheckResult"""
        verdicts = []
        for v in data.get('verdicts', []):
            if isinstance(v, dict):
                # Handle legacy records missing 'claim_english' field
                if 'claim_english' not in v:
                    v['claim_english'] = v.get('claim', '')
                verdicts.append(ClaimVerdict(**v))
            else:
                verdicts.append(v)
        
        return FactCheckResult(
            url=data.get('url', ''),
            transcript=data.get('transcript', ''),
            claims_found=data.get('claims_found', 0),
            verdicts=verdicts,
            overall_rating=data.get('overall_rating', ''),
            overall_confidence=data.get('overall_confidence', 0.0),
            summary=data.get('summary', ''),
            timestamp=data.get('timestamp', ''),
            language=data.get('language', 'english')
        )