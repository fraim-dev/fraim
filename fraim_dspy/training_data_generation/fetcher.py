import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from pymongo import MongoClient  # type: ignore[import-untyped]
from pymongo.database import Database  # type: ignore[import-untyped]

from .git import GitCodeExtractor
from .models import CVEData


logger = logging.getLogger(__name__)


class CVEDataFetcher:
    """Fetches CVE data from local MongoDB database populated by cve-search."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", mongo_db: str = "cvedb", extract_code: bool = True):
        """Initialize CVEDataFetcher with MongoDB connection.
        
        Args:
            mongo_uri: MongoDB connection URI
            mongo_db: MongoDB database name
            extract_code: Whether to extract code changes from references
        """
        self.client: MongoClient = MongoClient(mongo_uri)
        self.db: Database = self.client[mongo_db]
        self.extract_code = extract_code
        self.code_extractor = GitCodeExtractor() if extract_code else None

    def fetch_cves(
        self,
        severity: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        cwe_id: Optional[str] = None,
        max_results: int = 100,
    ) -> List[CVEData]:
        """Fetch CVEs from MongoDB based on search criteria.
        
        Args:
            severity: CVSS v3 severity level (e.g., HIGH, CRITICAL)
            start_date: Start date for CVE publication date range (YYYY-MM-DD)
            end_date: End date for CVE publication date range (YYYY-MM-DD)
            cwe_id: Comma-separated list of CWE IDs
            max_results: Maximum number of results to return
            
        Returns:
            List of CVEData objects matching the search criteria
        """
        query = self._build_mongo_query(severity, start_date, end_date, cwe_id)
        logger.debug(f"MongoDB query: {query}")
        
        all_cves: List[CVEData] = []
        try:
            # Query the cves collection
            cursor = self.db.cves.find(query)
            
            for cve_doc in cursor:
                cve = self._parse_cve(cve_doc)
                if cve:
                    logger.debug(f"CVE Parsed: {cve.cve_id}")
                    if len(cve.code_changes) > 0:
                        all_cves.append(cve)
                    else:
                        logger.info(f"No code changes found for {cve.cve_id} with references {cve.references}, skipping")
                        
                    if len(all_cves) >= max_results:
                        logger.info(f"Reached max results for {cwe_id}: {max_results}")
                        break
                        
        except Exception as e:
            logger.error(f"Error fetching CVEs from MongoDB: {e}")
            
        logger.info(f"Fetched {len(all_cves)} CVEs")
        return all_cves

    def _build_mongo_query(
        self,
        severity: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        cwe_ids: Optional[str],
    ) -> Dict[str, Any]:
        """Build MongoDB query based on search criteria."""
        query: Dict[str, Any] = {}
        
        # Add CVSS v3 or v4 requirement with optional severity filter
        severity_ranges = {
            'NONE': {'$lte': 0.0},
            'LOW': {'$gte': 0.1, '$lte': 3.9},
            'MEDIUM': {'$gte': 4.0, '$lte': 6.9},
            'HIGH': {'$gte': 7.0, '$lte': 8.9},
            'CRITICAL': {'$gte': 9.0, '$lte': 10.0}
        }
        
        cvss_conditions = []
        if severity:
            score_range = severity_ranges.get(severity.upper())
            if score_range:
                cvss_conditions.extend([
                    {'cvss3': {'$ne': None}, 'cvss3': score_range},
                    {'cvss4': {'$ne': None}, 'cvss4': score_range}
                ])
        else:
            cvss_conditions.extend([
                {'cvss3': {'$ne': None}},
                {'cvss4': {'$ne': None}}
            ])
            
        query['$or'] = cvss_conditions
            
        # Add date range filter
        date_query: Dict[str, Any] = {}
        if start_date:
            date_query['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            date_query['$lte'] = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        if date_query:
            query['published'] = date_query
            
        # Add CWE filter
        if cwe_ids:
            cwe_list = [cwe.strip() for cwe in cwe_ids.split(',')]
            query['cwe'] = {'$in': cwe_list}
        
        # Add GitHub references filter
        query['references'] = {
            '$elemMatch': {
                '$regex': 'github\\.com',
                '$options': 'i'
            }
        }
            
        return query

    def _parse_cve(self, cve_doc: Dict[str, Any]) -> Optional[CVEData]:
        """Parse CVE document from MongoDB into CVEData object.
        
        The MongoDB document structure from cve-search differs from the NVD API format.
        This method handles the conversion from cve-search format to our CVEData model.
        """
        try:
            cve_id = cve_doc.get('id', '')
            description = cve_doc.get('summary', 'No description')
            
            # Extract CWE IDs from vulnerable configuration
            cwe_ids: List[str] = []
            for config in cve_doc.get('vulnerable_configuration', []):
                if 'cwe' in config:
                    cwe_ids.append(config['cwe'])
            
            # Extract CVSS data and map score to severity
            cvss_score = float(cve_doc.get('cvss3', cve_doc.get('cvss4', 0.0)))
            
            # Map CVSS score to severity using the same ranges as in _build_mongo_query
            if cvss_score <= 0.0:
                severity = 'NONE'
            elif 0.1 <= cvss_score <= 3.9:
                severity = 'LOW'
            elif 4.0 <= cvss_score <= 6.9:
                severity = 'MEDIUM'
            elif 7.0 <= cvss_score <= 8.9:
                severity = 'HIGH'
            elif 9.0 <= cvss_score <= 10.0:
                severity = 'CRITICAL'
            else:
                severity = 'UNKNOWN'
                
            attack_vector = 'UNKNOWN'  # This field is not available in the new schema
            
            # Extract references
            references = [ref for ref in cve_doc.get('references', [])]
            
            # Determine vulnerability type
            vulnerability_type = self._determine_vulnerability_type(cwe_ids, description)
            
            # Extract dates
            published_date = cve_doc.get('Published', '')
            last_modified = cve_doc.get('Modified', '')
            
            # Extract code changes if needed
            code_changes = []
            if self.extract_code and self.code_extractor and references:
                logger.info(f"Extracting code changes for {cve_id}...")
                code_changes = self.code_extractor.extract_code_changes_from_references(references, cve_id)
                
            return CVEData(
                cve_id=cve_id,
                description=description,
                severity=severity,
                published_date=published_date,
                last_modified=last_modified,
                cwe_ids=cwe_ids,
                cvss_score=cvss_score,
                vulnerability_type=vulnerability_type,
                attack_vector=attack_vector,
                references=references,
                code_changes=code_changes,
            )
        except Exception as e:
            logger.error(f"Error parsing CVE: {e}")
            return None

    def _determine_vulnerability_type(self, cwe_ids: List[str], description: str) -> str:
        cwe_mappings = {
            'CWE-89': 'SQL Injection',
            'CWE-79': 'XSS',
            'CWE-22': 'Path Traversal',
            'CWE-78': 'Command Injection',
            'CWE-77': 'Command Injection',
            'CWE-94': 'Code Injection',
            'CWE-502': 'Insecure Deserialization',
            'CWE-918': 'SSRF',
            'CWE-200': 'Information Disclosure',
            'CWE-209': 'Information Disclosure',
            'CWE-798': 'Hardcoded Credentials',
            'CWE-259': 'Hardcoded Credentials',
            'CWE-352': 'CSRF',
            'CWE-327': 'Broken Cryptography',
            'CWE-326': 'Weak Encryption',
            'CWE-295': 'Certificate Validation',
            'CWE-319': 'Cleartext Transmission',
        }
        for cwe_id in cwe_ids:
            if cwe_id in cwe_mappings:
                return cwe_mappings[cwe_id]
        description_lower = description.lower()
        if any(term in description_lower for term in ['sql injection', 'sql', 'database']):
            return 'SQL Injection'
        elif any(term in description_lower for term in ['xss', 'cross-site scripting', 'script injection']):
            return 'XSS'
        elif any(term in description_lower for term in ['path traversal', 'directory traversal']):
            return 'Path Traversal'
        elif any(term in description_lower for term in ['command injection', 'command execution']):
            return 'Command Injection'
        elif any(term in description_lower for term in ['deserialization', 'pickle', 'serialize']):
            return 'Insecure Deserialization'
        elif any(term in description_lower for term in ['ssrf', 'server-side request forgery']):
            return 'SSRF'
        elif any(term in description_lower for term in ['csrf', 'cross-site request forgery']):
            return 'CSRF'
        elif any(term in description_lower for term in ['hardcoded', 'hard-coded', 'credential']):
            return 'Hardcoded Credentials'
        else:
            return 'Other'
