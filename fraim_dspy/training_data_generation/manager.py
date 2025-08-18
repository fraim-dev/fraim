import logging
import re
import urllib.parse
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional

from .fetcher import CVEDataFetcher
from .writers import (
    write_scanner_csv,
    write_scanner_yaml,
)
from .models import CVEData


logger = logging.getLogger(__name__)


class CVETrainingDataManager:
    """Main class for managing CVE-based training data generation."""

    def __init__(self, api_key: Optional[str] = None, extract_code: bool = True):
        # Initialize fetcher with default MongoDB settings and extract_code flag
        self.fetcher = CVEDataFetcher(extract_code=extract_code)

    def generate_training_data(
        self,
        vulnerability_types: List[str],
        output_dir: Path,
        max_cves_per_type: int = 10,
        severity: Optional[str] = None,
    ) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        scanner_data: List[CVEData] = []

        for owasp_control, cwes in self._get_owasp_cwe_mappings().items():
            logger.info(f"Fetching CVEs for {owasp_control}...")
            
            for cwe_id in cwes:
                logger.info(f"Fetching CVEs for {cwe_id}...")
                cves = self.fetcher.fetch_cves(
                    cwe_id=cwe_id,
                    max_results=max_cves_per_type,
                    severity=severity,
                )
                if not cves:
                    logger.warning(f"No CVEs found for {cwe_id}")
                    continue
                scanner_data.extend(cves)
                logger.info(f"Fetched {len(cves)} CVEs for {cwe_id}")
        write_scanner_csv(scanner_data, output_dir / "cve_training_data.csv")
        write_scanner_yaml(scanner_data, output_dir / "cve_training_data.yaml")
        if self.fetcher.code_extractor:
            self.fetcher.code_extractor.cleanup()
        logger.info(f"Training data saved to {output_dir}")

    def _get_keywords_for_vuln_type(self, vuln_type: str) -> List[str]:
        keyword_mapping = {
            'SQL Injection': ['sql injection', 'sql', 'database'],
            'XSS': ['xss', 'cross-site scripting', 'script injection'],
            'Path Traversal': ['path traversal', 'directory traversal'],
            'Command Injection': ['command injection', 'command execution'],
            'Insecure Deserialization': ['deserialization', 'pickle', 'serialization'],
            'SSRF': ['ssrf', 'server-side request forgery'],
            'CSRF': ['csrf', 'cross-site request forgery'],
            'Hardcoded Credentials': ['hardcoded', 'hard-coded credentials'],
        }
        return keyword_mapping.get(vuln_type, [vuln_type.lower()])

    def _get_owasp_cwe_mappings(self) -> Dict[str, List[str]]:
        """Fetches OWASP Top 10 to CWE mappings from the OWASP website."""
        base_url = "https://owasp.org/Top10"
        owasp_controls = [
            "A01_2021-Broken_Access_Control",
            "A02_2021-Cryptographic_Failures",
            "A03_2021-Injection",
            "A04_2021-Insecure_Design",
            "A05_2021-Security_Misconfiguration",
            "A06_2021-Vulnerable_and_Outdated_Components",
            "A07_2021-Identification_and_Authentication_Failures",
            "A08_2021-Software_and_Data_Integrity_Failures",
            "A09_2021-Security_Logging_and_Monitoring_Failures",
            "A10_2021-Server-Side_Request_Forgery_%28SSRF%29"
        ]
        
        mappings = {}
        for control in owasp_controls:
            # Extract control name from the URL
            control_name = control.split("-", 1)[1].replace("_", " ")
                
            try:
                url = f"{base_url}/{control}/"
                response = requests.get(url)
                response.raise_for_status()
                content = response.text
                
                # Find CWE mappings section
                cwe_pattern = r"CWE-(\d+)\s+([^\n]+)"
                cwe_matches = re.findall(cwe_pattern, content)
                
                # Create list of CWE IDs and descriptions
                cwe_list = [f"CWE-{cwe_id}" for cwe_id, _ in cwe_matches]
                
                if cwe_list:
                    mappings[control_name] = cwe_list
                else:
                    logger.warning(f"No CWE mappings found for {control_name}")
            
            except requests.RequestException as e:
                logger.error(f"Failed to fetch CWE mappings for {control_name}: {e}")
                continue
        
        return mappings


