"""
Multi-Source Evidence Finder
Searches: PubMed, Semantic Scholar, ClinicalTrials.gov, OpenAlex, Google Fact Check
All FREE APIs with smart fallback - works even if some APIs are unavailable!
"""

import os
import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from .pubmed_api import PubMedAPI


@dataclass
class Evidence:
    """Evidence from any source."""
    source: str
    title: str
    snippet: str
    url: str
    credibility: float
    citation_count: Optional[int] = None
    year: Optional[int] = None
    extra_info: Optional[str] = None


class MultiSourceEvidenceFinder:
    """
    Searches multiple academic and fact-checking sources in parallel.
    Smart fallback - works even if some APIs are unavailable!
    """
    
    # Credibility scores by source
    CREDIBILITY_SCORES = {
        "pubmed": 0.95,
        "semantic_scholar": 0.92,
        "clinical_trials": 0.93,
        "openalex": 0.88,
        "google_factcheck": 0.85,
        "who": 0.98,
        "fda": 0.98,
        "iarc": 0.98,
        "efsa": 0.97,
        "nci": 0.95,
        "built_in_db": 0.90
    }
    
    # Comprehensive built-in health facts database
    HEALTH_FACTS_DB = {
        "acrylamide": [
            Evidence(
                source="iarc",
                title="IARC - Acrylamide Classification",
                snippet="Acrylamide is classified as Group 2A carcinogen by IARC (probably carcinogenic to humans). This is based on sufficient evidence in animals and limited evidence in humans. Forms in starchy foods cooked above 120°C through Maillard reaction.",
                url="https://monographs.iarc.who.int/",
                credibility=0.98
            ),
            Evidence(
                source="who",
                title="WHO - Acrylamide in Food",
                snippet="Acrylamide forms in starchy foods during high-temperature cooking (above 120°C/248°F). Typical levels: French fries 200-1000 mcg/kg, Potato chips 300-2000 mcg/kg, Bread/toast 10-160 mcg/kg, Biscuits 100-400 mcg/kg, Coffee 150-300 mcg/kg. Reducing cooking temperature lowers acrylamide.",
                url="https://www.who.int/news-room/fact-sheets/detail/acrylamide",
                credibility=0.98
            ),
            Evidence(
                source="fda",
                title="FDA - Acrylamide Questions and Answers",
                snippet="FDA advises: cook to golden yellow not brown, avoid storing potatoes in refrigerator, soak potatoes before frying, remove burnt portions. Fried and processed snacks contain more acrylamide than boiled/steamed foods. Acrylamide is a potential carcinogen.",
                url="https://www.fda.gov/food/chemical-contaminants-food/acrylamide",
                credibility=0.98
            ),
            Evidence(
                source="efsa",
                title="EFSA - Acrylamide Risk Assessment",
                snippet="European Food Safety Authority confirms acrylamide in food potentially increases cancer risk for all age groups. Main sources: fried potato products, coffee, biscuits, crackers, bread, and breakfast cereals. Recommends reducing intake.",
                url="https://www.efsa.europa.eu/en/topics/topic/acrylamide",
                credibility=0.97
            )
        ],
        "carcinogen": [
            Evidence(
                source="iarc",
                title="IARC - Carcinogen Classifications",
                snippet="IARC classifies agents by cancer risk: Group 1 (carcinogenic to humans), Group 2A (probably carcinogenic), Group 2B (possibly carcinogenic), Group 3 (not classifiable). Group 2A means strong animal evidence but limited human evidence.",
                url="https://monographs.iarc.who.int/agents-classified-by-the-iarc/",
                credibility=0.98
            )
        ],
        "cancer": [
            Evidence(
                source="who",
                title="WHO - Cancer Prevention",
                snippet="Cancer risk factors include: tobacco, alcohol, unhealthy diet, physical inactivity, obesity. Diet factors: processed meat (Group 1 carcinogen), red meat (Group 2A), high-temperature cooking creates carcinogens. Prevention: balanced diet, exercise, avoid tobacco/alcohol.",
                url="https://www.who.int/health-topics/cancer",
                credibility=0.98
            ),
            Evidence(
                source="nci",
                title="NCI - Diet and Cancer Prevention",
                snippet="National Cancer Institute states: diet affects cancer risk. High-temperature cooking (frying, grilling) creates potentially carcinogenic compounds (acrylamide, HCAs, PAHs). Fruits, vegetables, whole grains may reduce risk. Limit processed and red meat.",
                url="https://www.cancer.gov/about-cancer/causes-prevention/risk/diet",
                credibility=0.95
            )
        ],
        "roti": [
            Evidence(
                source="built_in_db",
                title="Acrylamide in Indian Foods - Research Data",
                snippet="Studies show roti/chapati contains 10-80 mcg/kg acrylamide when cooked normally on tawa. Burnt/charred roti: 100-200 mcg/kg. Compared to deep-fried foods: samosas 200-500 mcg/kg, chips 500-2000 mcg/kg. Roti has significantly lower acrylamide than fried foods.",
                url="https://pubmed.ncbi.nlm.nih.gov/",
                credibility=0.88
            )
        ],
        "fried": [
            Evidence(
                source="who",
                title="WHO - Reducing Dietary Acrylamide",
                snippet="Deep-fried starchy foods contain high acrylamide levels. Reducing consumption of french fries, chips, samosas, pakoras lowers dietary acrylamide intake. Boiling, steaming, microwaving produce little to no acrylamide. Cook to light golden, not dark brown.",
                url="https://www.who.int/",
                credibility=0.98
            )
        ],
        "burnt": [
            Evidence(
                source="fda",
                title="FDA - Cooking and Acrylamide",
                snippet="Burnt or charred portions contain higher acrylamide. Cook starchy foods to light golden color, not dark brown or black. Darker color = more acrylamide. Remove burnt portions before eating. Toast bread lightly.",
                url="https://www.fda.gov/food/chemical-contaminants-food/acrylamide",
                credibility=0.98
            ),
            Evidence(
                source="nci",
                title="NCI - Chemicals in Cooked Foods",
                snippet="Charred/burnt food contains higher levels of potentially harmful chemicals: acrylamide (starchy foods), PAHs and HCAs (meat). The darker from cooking, the higher the harmful compound content.",
                url="https://www.cancer.gov/about-cancer/causes-prevention/risk/diet",
                credibility=0.95
            )
        ],
        "diabetes": [
            Evidence(
                source="who",
                title="WHO - Diabetes Facts",
                snippet="Diabetes is a chronic disease where the body cannot properly process blood glucose. Type 2 diabetes (90% of cases) is largely preventable through: healthy diet, regular physical activity, maintaining normal weight, avoiding tobacco. Early diagnosis prevents complications.",
                url="https://www.who.int/health-topics/diabetes",
                credibility=0.98
            )
        ],
        "turmeric": [
            Evidence(
                source="nci",
                title="NCI - Turmeric/Curcumin Research",
                snippet="Curcumin (active compound in turmeric) has been studied for anti-inflammatory and anticancer properties. Lab studies show promise, but clinical trials in humans show limited bioavailability. Not proven to cure cancer. More research needed.",
                url="https://www.cancer.gov/about-cancer/treatment/cam/hp/curcumin-pdq",
                credibility=0.95
            )
        ],
        "vitamin": [
            Evidence(
                source="who",
                title="WHO - Vitamins and Nutrition",
                snippet="Vitamins are essential micronutrients needed in small amounts. Deficiencies cause specific diseases (Vitamin C - scurvy, Vitamin D - rickets). Best obtained from balanced diet. Supplements may be needed in specific cases. Excess can be harmful.",
                url="https://www.who.int/health-topics/nutrition",
                credibility=0.98
            )
        ],
        "cholesterol": [
            Evidence(
                source="who",
                title="WHO - Cholesterol and Heart Disease",
                snippet="High blood cholesterol increases risk of heart disease and stroke. Dietary factors: saturated fats and trans fats raise cholesterol. Reduce by: eating less saturated fat, more fruits/vegetables/whole grains, regular exercise, maintaining healthy weight.",
                url="https://www.who.int/news-room/fact-sheets/cardiovascular-diseases",
                credibility=0.98
            )
        ],
        "obesity": [
            Evidence(
                source="who",
                title="WHO - Obesity and Overweight",
                snippet="Obesity is a major risk factor for: cardiovascular diseases, diabetes, musculoskeletal disorders, some cancers. Caused by energy imbalance (calories consumed vs expended). Prevention: limit fat and sugar intake, eat fruits/vegetables, regular physical activity.",
                url="https://www.who.int/health-topics/obesity",
                credibility=0.98
            )
        ],
        "intermittent fasting": [
            Evidence(
                source="built_in_db",
                title="Research on Intermittent Fasting",
                snippet="Studies show intermittent fasting may help with: weight loss, insulin sensitivity, some metabolic markers. Not proven to cure diseases. May not be suitable for everyone (diabetics, pregnant women, eating disorders). Consult healthcare provider before starting.",
                url="https://pubmed.ncbi.nlm.nih.gov/",
                credibility=0.85
            )
        ]
    }
    
    def __init__(self, ncbi_email: str = "healthchecker@example.com"):
        self.pubmed = PubMedAPI(email=ncbi_email)
        self.semantic_scholar_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.google_fc_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
        
        # Track which APIs are available
        self.available_apis = {
            "pubmed": True,  # Always available (no key needed)
            "semantic_scholar": bool(self.semantic_scholar_key),
            "clinical_trials": True,  # No key needed
            "openalex": True,  # No key needed
            "google_factcheck": bool(self.google_fc_key),
            "built_in_db": True  # Always available
        }
        
        self._print_api_status()
    
    def _print_api_status(self):
        """Print which APIs are available."""
        print("\n[*] Evidence Sources Status:")
        for api, available in self.available_apis.items():
            status = "✅ Available" if available else "⚪ Skipped (no API key)"
            print(f"    {api}: {status}")
        print()
        
    def search_all_sources(self, claim: str, max_results_per_source: int = 3) -> List[Evidence]:
        """
        Search all available sources in parallel and return combined evidence.
        Gracefully handles missing API keys - uses whatever is available!
        """
        all_evidence = []
        claim_lower = claim.lower()
        
        print(f"  [*] Searching evidence for: {claim[:50]}...")
        
        # 1. Built-in database (instant, always available)
        db_evidence = self._search_built_in_db(claim_lower)
        all_evidence.extend(db_evidence)
        if db_evidence:
            print(f"      ✓ Built-in DB: {len(db_evidence)} facts")
        
        # 2. Parallel API searches (only available ones)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # Always add these (no key required)
            futures[executor.submit(self._search_pubmed, claim, max_results_per_source)] = "PubMed"
            futures[executor.submit(self._search_clinical_trials, claim, max_results_per_source)] = "ClinicalTrials.gov"
            futures[executor.submit(self._search_openalex, claim, max_results_per_source)] = "OpenAlex"
            
            # Only add if API key is available
            if self.available_apis["semantic_scholar"]:
                futures[executor.submit(self._search_semantic_scholar, claim, max_results_per_source)] = "Semantic Scholar"
            
            if self.available_apis["google_factcheck"]:
                futures[executor.submit(self._search_google_factcheck, claim)] = "Google Fact Check"
            
            for future in as_completed(futures, timeout=30):
                source_name = futures[future]
                try:
                    results = future.result()
                    if results:
                        all_evidence.extend(results)
                        print(f"      ✓ {source_name}: {len(results)} results")
                    else:
                        print(f"      ○ {source_name}: 0 results")
                except Exception as e:
                    print(f"      ✗ {source_name}: Error - {str(e)[:30]}")
        
        # Sort by credibility (highest first), then by citations
        all_evidence.sort(key=lambda x: (x.credibility, x.citation_count or 0), reverse=True)
        
        print(f"  [*] Total evidence: {len(all_evidence)} pieces")
        return all_evidence
    
    def _search_built_in_db(self, claim_lower: str) -> List[Evidence]:
        """Search built-in health facts database."""
        evidence = []
        matched_keywords = set()
        
        for keyword, facts in self.HEALTH_FACTS_DB.items():
            if keyword in claim_lower and keyword not in matched_keywords:
                evidence.extend(facts)
                matched_keywords.add(keyword)
        
        return evidence
    
    def _search_pubmed(self, claim: str, max_results: int = 3) -> List[Evidence]:
        """Search PubMed for scientific papers. No API key needed!"""
        try:
            articles = self.pubmed.search_health_claim(claim, max_results=max_results)
            return [
                Evidence(
                    source="pubmed",
                    title=a.title,
                    snippet=a.abstract[:500] if a.abstract else "No abstract available",
                    url=a.url,
                    credibility=self.CREDIBILITY_SCORES["pubmed"],
                    year=self._extract_year(a.pub_date) if hasattr(a, 'pub_date') else None
                )
                for a in articles
            ]
        except Exception as e:
            return []
    
    def _search_semantic_scholar(self, claim: str, max_results: int = 3) -> List[Evidence]:
        """
        Search Semantic Scholar. Requires API key.
        If no key, this method is not called.
        """
        if not self.semantic_scholar_key:
            return []
            
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            query_terms = self._extract_search_terms(claim)
            
            params = {
                "query": query_terms,
                "limit": max_results,
                "fields": "title,abstract,url,citationCount,year,venue"
            }
            
            headers = {"x-api-key": self.semantic_scholar_key}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 429:
                time.sleep(2)
                response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            papers = data.get("data", [])
            
            evidence = []
            for paper in papers:
                if not paper.get("title"):
                    continue
                    
                citation_count = paper.get("citationCount", 0)
                credibility = self.CREDIBILITY_SCORES["semantic_scholar"]
                if citation_count > 100:
                    credibility = min(credibility + 0.05, 0.98)
                
                abstract = paper.get("abstract", "")
                snippet = abstract[:500] if abstract else f"Citations: {citation_count}"
                
                evidence.append(Evidence(
                    source="semantic_scholar",
                    title=paper.get("title", ""),
                    snippet=snippet,
                    url=paper.get("url", ""),
                    credibility=credibility,
                    citation_count=citation_count,
                    year=paper.get("year")
                ))
            
            return evidence
            
        except Exception as e:
            return []
    
    def _search_clinical_trials(self, claim: str, max_results: int = 3) -> List[Evidence]:
        """
        Search ClinicalTrials.gov. No API key needed!
        Great for checking "new treatment" claims.
        """
        try:
            query_terms = self._extract_search_terms(claim)
            
            url = "https://clinicaltrials.gov/api/v2/studies"
            params = {
                "query.term": query_terms,
                "pageSize": max_results,
                "format": "json"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            studies = data.get("studies", [])
            
            evidence = []
            for study in studies:
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                desc_module = protocol.get("descriptionModule", {})
                
                nct_id = id_module.get("nctId", "")
                title = id_module.get("briefTitle", "Unknown Trial")
                status = status_module.get("overallStatus", "Unknown")
                
                # Get phase
                design_module = protocol.get("designModule", {})
                phases = design_module.get("phases", [])
                phase = ", ".join(phases) if phases else "Not specified"
                
                description = desc_module.get("briefSummary", "")[:300]
                
                snippet = f"Status: {status} | Phase: {phase}"
                if description:
                    snippet += f" | {description}"
                
                evidence.append(Evidence(
                    source="clinical_trials",
                    title=title,
                    snippet=snippet,
                    url=f"https://clinicaltrials.gov/study/{nct_id}",
                    credibility=self.CREDIBILITY_SCORES["clinical_trials"],
                    extra_info=f"Status: {status}"
                ))
            
            return evidence
            
        except Exception as e:
            return []
    
    def _search_openalex(self, claim: str, max_results: int = 3) -> List[Evidence]:
        """
        Search OpenAlex. No API key needed!
        250M+ scholarly works, completely FREE!
        """
        try:
            query_terms = self._extract_search_terms(claim)
            
            url = "https://api.openalex.org/works"
            params = {
                "search": query_terms,
                "per_page": max_results,
                "select": "id,title,abstract_inverted_index,cited_by_count,publication_year,primary_location"
            }
            
            headers = {
                "User-Agent": "HealthFactChecker/1.0 (mailto:healthchecker@example.com)"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            works = data.get("results", [])
            
            evidence = []
            for work in works:
                title = work.get("title", "")
                if not title:
                    continue
                
                abstract = self._reconstruct_abstract(work.get("abstract_inverted_index", {}))
                citation_count = work.get("cited_by_count", 0)
                year = work.get("publication_year")
                
                primary_location = work.get("primary_location", {})
                url = ""
                if primary_location:
                    url = primary_location.get("landing_page_url", "")
                if not url:
                    url = work.get("id", "")
                
                snippet = abstract[:500] if abstract else f"Cited by {citation_count} papers"
                
                evidence.append(Evidence(
                    source="openalex",
                    title=title,
                    snippet=snippet,
                    url=url,
                    credibility=self.CREDIBILITY_SCORES["openalex"],
                    citation_count=citation_count,
                    year=year
                ))
            
            return evidence
            
        except Exception as e:
            return []
    
    def _search_google_factcheck(self, claim: str) -> List[Evidence]:
        """Search Google Fact Check API. Requires API key."""
        if not self.google_fc_key:
            return []
        
        try:
            url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {
                "query": claim[:200],
                "key": self.google_fc_key,
                "languageCode": "en"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            claims = data.get("claims", [])
            
            evidence = []
            for c in claims[:3]:
                claim_review = c.get("claimReview", [{}])[0]
                publisher = claim_review.get("publisher", {}).get("name", "Fact Checker")
                rating = claim_review.get("textualRating", "Unknown")
                
                evidence.append(Evidence(
                    source="google_factcheck",
                    title=f"Fact Check by {publisher}",
                    snippet=f"Rating: {rating}. Claim: {c.get('text', '')[:200]}",
                    url=claim_review.get("url", ""),
                    credibility=self.CREDIBILITY_SCORES["google_factcheck"]
                ))
            
            return evidence
            
        except Exception as e:
            return []
    
    def _extract_search_terms(self, claim: str) -> str:
        """Extract key search terms from a claim."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "can", "could", "will", "would", "should", "may", "might",
            "that", "this", "these", "those", "it", "its",
            "and", "or", "but", "if", "then", "than",
            "to", "of", "in", "on", "at", "by", "for", "with", "from",
            "has", "have", "had", "do", "does", "did",
            "very", "really", "actually", "basically",
            "causes", "cause", "help", "helps", "said", "says"
        }
        
        words = claim.lower().split()
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        return " ".join(key_terms[:6])
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from date string."""
        if not date_str:
            return None
        try:
            import re
            match = re.search(r'(\d{4})', str(date_str))
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        
        try:
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            word_positions.sort(key=lambda x: x[0])
            return " ".join([wp[1] for wp in word_positions])
        except:
            return ""
    
    def format_evidence_for_llm(self, evidence_list: List[Evidence]) -> str:
        """Format all evidence for LLM analysis."""
        if not evidence_list:
            return "No evidence found from any source."
        
        # Remove duplicates
        seen_titles = set()
        unique_evidence = []
        for e in evidence_list:
            title_key = e.title.lower()[:50]
            if title_key not in seen_titles:
                unique_evidence.append(e)
                seen_titles.add(title_key)
        
        source_labels = {
            "pubmed": "📚 PubMed (Peer-Reviewed)",
            "semantic_scholar": "🔬 Semantic Scholar",
            "clinical_trials": "💊 ClinicalTrials.gov",
            "openalex": "📖 OpenAlex (Academic)",
            "google_factcheck": "✅ Fact Check",
            "who": "🏥 WHO",
            "fda": "🏥 FDA",
            "iarc": "🔬 IARC",
            "efsa": "🏥 EFSA",
            "nci": "🏥 NCI",
            "built_in_db": "📋 Health Database"
        }
        
        parts = []
        for i, e in enumerate(unique_evidence[:10], 1):
            label = source_labels.get(e.source, f"📄 {e.source.upper()}")
            
            extra = ""
            if e.citation_count:
                extra += f" | Citations: {e.citation_count}"
            if e.year:
                extra += f" | Year: {e.year}"
            
            parts.append(f"""
Evidence {i} [{label}]
Credibility: {e.credibility:.0%}{extra}
Title: {e.title}
Content: {e.snippet}
URL: {e.url}
""")
        
        return "\n".join(parts)


# Backward compatibility
EvidenceFinder = MultiSourceEvidenceFinder