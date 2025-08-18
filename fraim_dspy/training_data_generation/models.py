from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CodeChange:
    """Represents a code change from a vulnerability fix."""
    vulnerable_code: str
    fixed_code: str
    commit_hash: str
    repo_url: str


@dataclass
class CVEData:
    """Represents a CVE with extracted information."""
    cve_id: str
    description: str
    severity: str
    published_date: str
    last_modified: str
    cwe_ids: List[str]
    cvss_score: float
    vulnerability_type: str
    attack_vector: str
    references: List[str]
    code_changes: List[CodeChange]
