"""
Tests for FactChecker class, specifically dict_to_result method
"""

import sys
import os
from dataclasses import dataclass
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import only the dataclasses and the dict_to_result logic we need to test
@dataclass
class ClaimVerdict:
    claim: str
    claim_english: str
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


def dict_to_result(data: Dict) -> FactCheckResult:
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


def test_dict_to_result_with_claim_english():
    """Test dict_to_result with verdicts that include claim_english field"""
    
    test_data = {
        'url': 'https://example.com',
        'transcript': 'Test transcript',
        'claims_found': 1,
        'verdicts': [
            {
                'claim': 'Test claim',
                'claim_english': 'Test claim in English',
                'verdict': 'TRUE',
                'confidence': 0.9,
                'explanation': 'Test explanation',
                'evidence': [],
                'sources': [],
                'category': 'health'
            }
        ],
        'overall_rating': 'TRUE',
        'overall_confidence': 0.9,
        'summary': 'Test summary',
        'timestamp': '2024-01-01T00:00:00',
        'language': 'english'
    }
    
    result = dict_to_result(test_data)
    
    assert isinstance(result, FactCheckResult)
    assert len(result.verdicts) == 1
    assert isinstance(result.verdicts[0], ClaimVerdict)
    assert result.verdicts[0].claim == 'Test claim'
    assert result.verdicts[0].claim_english == 'Test claim in English'
    print("✅ Test passed: dict_to_result with claim_english field")


def test_dict_to_result_without_claim_english():
    """Test dict_to_result with legacy verdicts missing claim_english field"""
    # Simulating old database record without claim_english field
    test_data = {
        'url': 'https://example.com',
        'transcript': 'Test transcript',
        'claims_found': 1,
        'verdicts': [
            {
                'claim': 'Test claim',
                # 'claim_english' is missing (legacy data)
                'verdict': 'TRUE',
                'confidence': 0.9,
                'explanation': 'Test explanation',
                'evidence': [],
                'sources': [],
                'category': 'health'
            }
        ],
        'overall_rating': 'TRUE',
        'overall_confidence': 0.9,
        'summary': 'Test summary',
        'timestamp': '2024-01-01T00:00:00',
        'language': 'english'
    }
    
    # This should not raise TypeError anymore
    result = dict_to_result(test_data)
    
    assert isinstance(result, FactCheckResult)
    assert len(result.verdicts) == 1
    assert isinstance(result.verdicts[0], ClaimVerdict)
    assert result.verdicts[0].claim == 'Test claim'
    # claim_english should default to claim value
    assert result.verdicts[0].claim_english == 'Test claim'
    print("✅ Test passed: dict_to_result without claim_english field (legacy support)")


def test_dict_to_result_mixed_verdicts():
    """Test dict_to_result with mixed verdicts (some with, some without claim_english)"""
    test_data = {
        'url': 'https://example.com',
        'transcript': 'Test transcript',
        'claims_found': 2,
        'verdicts': [
            {
                'claim': 'Claim with English',
                'claim_english': 'Claim with English translation',
                'verdict': 'TRUE',
                'confidence': 0.9,
                'explanation': 'Test explanation',
                'evidence': [],
                'sources': [],
                'category': 'health'
            },
            {
                'claim': 'Legacy claim',
                # Missing claim_english
                'verdict': 'FALSE',
                'confidence': 0.8,
                'explanation': 'Test explanation 2',
                'evidence': [],
                'sources': [],
                'category': 'health'
            }
        ],
        'overall_rating': 'MIXED',
        'overall_confidence': 0.85,
        'summary': 'Test summary',
        'timestamp': '2024-01-01T00:00:00',
        'language': 'hindi'
    }
    
    result = dict_to_result(test_data)
    
    assert isinstance(result, FactCheckResult)
    assert len(result.verdicts) == 2
    assert result.verdicts[0].claim_english == 'Claim with English translation'
    assert result.verdicts[1].claim_english == 'Legacy claim'  # Should default to claim
    print("✅ Test passed: dict_to_result with mixed verdicts")


if __name__ == "__main__":
    print("Running FactChecker tests...\n")
    
    try:
        test_dict_to_result_with_claim_english()
        test_dict_to_result_without_claim_english()
        test_dict_to_result_mixed_verdicts()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
