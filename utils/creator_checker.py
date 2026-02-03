"""
Creator Credibility Checker
Analyzes Instagram creator's posting patterns and credibility
"""

import re
from typing import Dict, List, Optional
import instaloader


class CreatorCredibilityChecker:
    """Check Instagram creator's credibility for health content."""
    
    # Keywords that suggest medical credentials
    CREDENTIAL_KEYWORDS = [
        "dr", "doctor", "md", "phd", "nutritionist", "dietitian",
        "physician", "surgeon", "nurse", "rn", "therapist",
        "researcher", "scientist", "professor", "expert",
        "certified", "licensed", "board certified"
    ]
    
    # Red flag keywords
    RED_FLAG_KEYWORDS = [
        "miracle", "cure", "secret", "doctors hate",
        "big pharma", "natural cure", "detox",
        "lose weight fast", "guaranteed", "100%"
    ]
    
    def __init__(self):
        self.loader = instaloader.Instaloader(quiet=True)
    
    def check_creator(self, username: str) -> Dict:
        """
        Analyze creator's credibility.
        
        Args:
            username: Instagram username
            
        Returns:
            Dictionary with credibility assessment
        """
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            # Extract bio information
            bio = profile.biography.lower() if profile.biography else ""
            
            # Check for credentials
            has_credentials = any(keyword in bio for keyword in self.CREDENTIAL_KEYWORDS)
            
            # Check for red flags
            red_flags = [flag for flag in self.RED_FLAG_KEYWORDS if flag in bio]
            
            # Calculate credibility score
            credibility_score = 0.5  # Base score
            
            if profile.is_verified:
                credibility_score += 0.2
            
            if has_credentials:
                credibility_score += 0.2
            
            if red_flags:
                credibility_score -= 0.1 * len(red_flags)
            
            # Cap between 0 and 1
            credibility_score = max(0.0, min(1.0, credibility_score))
            
            warnings = []
            if red_flags:
                warnings.append(f"Bio contains red flags: {', '.join(red_flags)}")
            
            if not has_credentials and not profile.is_verified:
                warnings.append("No medical credentials found in bio")
            
            return {
                "username": username,
                "verified": profile.is_verified,
                "credibility_score": credibility_score,
                "has_credentials": has_credentials,
                "red_flags": red_flags,
                "warnings": warnings,
                "bio": profile.biography,
                "followers": profile.followers,
                "following": profile.followees
            }
            
        except Exception as e:
            return {
                "username": username,
                "verified": False,
                "credibility_score": 0.5,
                "has_credentials": False,
                "red_flags": [],
                "warnings": [f"Could not analyze creator: {str(e)}"],
                "bio": "",
                "followers": 0,
                "following": 0
            }
    
    def extract_username_from_url(self, url: str) -> Optional[str]:
        """Extract username from Instagram URL"""
        patterns = [
            r'instagram\.com/([^/]+)',
            r'instagram\.com/reels/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None