"""
Test to verify that dict_to_result doesn't mutate the input dictionary
"""

import sys
import os
import copy

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass
from typing import List, Dict


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
            # Create a new dict to avoid mutating the input
            if 'claim_english' not in v:
                v = {**v, 'claim_english': v.get('claim', '')}
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


def test_no_mutation_of_input():
    """Verify that dict_to_result doesn't mutate the input dictionary"""
    print("Testing that dict_to_result doesn't mutate input data...")
    
    # Create test data without claim_english
    original_data = {
        'url': 'https://example.com',
        'transcript': 'Test',
        'claims_found': 1,
        'verdicts': [
            {
                'claim': 'Test claim',
                'verdict': 'TRUE',
                'confidence': 0.9,
                'explanation': 'Test',
                'evidence': [],
                'sources': [],
                'category': 'health'
            }
        ],
        'overall_rating': 'TRUE',
        'overall_confidence': 0.9,
        'summary': 'Test',
        'timestamp': '2024-01-01T00:00:00',
        'language': 'english'
    }
    
    # Create a deep copy to compare later
    original_copy = copy.deepcopy(original_data)
    
    # Call dict_to_result
    result = dict_to_result(original_data)
    
    # Verify the result is correct
    assert result.verdicts[0].claim_english == 'Test claim'
    
    # Verify the original data wasn't mutated
    assert original_data == original_copy, "Original data was mutated!"
    assert 'claim_english' not in original_data['verdicts'][0], \
        "claim_english was added to the original data!"
    
    print("✅ Test passed: Input data was not mutated")


if __name__ == "__main__":
    try:
        test_no_mutation_of_input()
        print("\n✅ All mutation tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
