"""
PubMed API Handler - Free scientific article search
Uses NCBI E-utilities (completely free, no API key required for basic use)
"""

import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class PubMedArticle:
    """Represents a PubMed article."""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    pub_date: str
    doi: Optional[str] = None
    url: str = ""
    
    def __post_init__(self):
        self.url = f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class PubMedAPI:
    """
    Free PubMed API wrapper using NCBI E-utilities.
    
    Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    Rate limit: 3 requests/second without API key, 10/sec with key
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: str = "healthchecker@example.com", api_key: Optional[str] = None):
        """
        Initialize PubMed API.
        
        Args:
            email: Email for NCBI (required by their terms)
            api_key: Optional NCBI API key for higher rate limits
        """
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 0.34 if api_key else 0.5  # Rate limiting
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, query: str, max_results: int = 10, 
               filter_reviews: bool = True) -> List[str]:
        """
        Search PubMed for articles matching query.
        
        Args:
            query: Search query (supports PubMed syntax)
            max_results: Maximum number of results
            filter_reviews: If True, prioritize review articles
            
        Returns:
            List of PubMed IDs (PMIDs)
        """
        self._rate_limit()
        
        # Enhance query for health claims
        enhanced_query = query
        if filter_reviews:
            enhanced_query = f"({query}) AND (systematic review[pt] OR meta-analysis[pt] OR review[pt])"
        
        params = {
            "db": "pubmed",
            "term": enhanced_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        response = self.session.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_articles(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch full article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []
        
        self._rate_limit()
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        response = self.session.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
        response.raise_for_status()
        
        return self._parse_articles_xml(response.text)
    
    def _parse_articles_xml(self, xml_text: str) -> List[PubMedArticle]:
        """Parse PubMed XML response into article objects."""
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall(".//PubmedArticle"):
                try:
                    # Extract PMID
                    pmid_elem = article_elem.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    # Extract title
                    title_elem = article_elem.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    # Extract abstract
                    abstract_parts = []
                    for abstract_elem in article_elem.findall(".//AbstractText"):
                        label = abstract_elem.get("Label", "")
                        text = abstract_elem.text or ""
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                    abstract = " ".join(abstract_parts)
                    
                    # Extract authors
                    authors = []
                    for author_elem in article_elem.findall(".//Author"):
                        last_name = author_elem.find("LastName")
                        first_name = author_elem.find("ForeName")
                        if last_name is not None and first_name is not None:
                            authors.append(f"{last_name.text} {first_name.text}")
                    
                    # Extract journal
                    journal_elem = article_elem.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""
                    
                    # Extract publication date
                    pub_date_elem = article_elem.find(".//PubDate")
                    if pub_date_elem is not None:
                        year = pub_date_elem.find("Year")
                        month = pub_date_elem.find("Month")
                        pub_date = f"{year.text if year is not None else ''} {month.text if month is not None else ''}".strip()
                    else:
                        pub_date = ""
                    
                    # Extract DOI
                    doi = None
                    for id_elem in article_elem.findall(".//ArticleId"):
                        if id_elem.get("IdType") == "doi":
                            doi = id_elem.text
                            break
                    
                    articles.append(PubMedArticle(
                        pmid=pmid,
                        title=title,
                        abstract=abstract,
                        authors=authors[:5],  # Limit authors
                        journal=journal,
                        pub_date=pub_date,
                        doi=doi
                    ))
                    
                except Exception:
                    continue
                    
        except ET.ParseError:
            pass
        
        return articles
    
    def search_health_claim(self, claim: str, max_results: int = 5) -> List[PubMedArticle]:
        """
        Search PubMed for evidence related to a health claim.
        
        Args:
            claim: Health claim to verify
            max_results: Maximum articles to return
            
        Returns:
            List of relevant PubMedArticle objects
        """
        # Clean and optimize query for PubMed
        # Remove common words and focus on medical terms
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'will', 'can', 
                      'could', 'should', 'would', 'may', 'might', 'must', 'shall',
                      'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
                      'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where',
                      'when', 'why', 'how', 'if', 'then', 'else', 'and', 'or', 'not',
                      'but', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for',
                      'with', 'about', 'against', 'between', 'into', 'through', 'during',
                      'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
                      'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further',
                      'once', 'here', 'there', 'all', 'each', 'few', 'more', 'most',
                      'other', 'some', 'such', 'no', 'nor', 'only', 'own', 'same', 'so',
                      'than', 'too', 'very', 'just', 'also', 'now', 'your', 'my', 'our'}
        
        words = claim.lower().split()
        query_words = [w for w in words if w not in stop_words and len(w) > 2]
        query = " ".join(query_words[:10])  # Limit query length
        
        # Search for articles
        pmids = self.search(query, max_results=max_results, filter_reviews=True)
        
        # If no review articles found, try without filter
        if not pmids:
            pmids = self.search(query, max_results=max_results, filter_reviews=False)
        
        if not pmids:
            return []
        
        return self.fetch_articles(pmids)
    
    def get_evidence_summary(self, claim: str) -> Dict:
        """
        Get a summary of scientific evidence for a claim.
        
        Args:
            claim: Health claim to check
            
        Returns:
            Dictionary with evidence summary
        """
        articles = self.search_health_claim(claim)
        
        return {
            "claim": claim,
            "articles_found": len(articles),
            "articles": [
                {
                    "title": a.title,
                    "abstract": a.abstract[:500] + "..." if len(a.abstract) > 500 else a.abstract,
                    "journal": a.journal,
                    "year": a.pub_date,
                    "url": a.url,
                    "authors": a.authors
                }
                for a in articles
            ],
            "sources": [a.url for a in articles]
        }